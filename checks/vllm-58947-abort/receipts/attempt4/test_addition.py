

@pytest.mark.parametrize(
    "receive_before_abort",
    [False, True],
    ids=["abort-before-receive", "abort-after-receive"],
)
def test_aborted_remote_load_releases_capacity_after_receive(receive_before_abort):
    """Abort clears deferred admission state without reusing an in-flight load's
    blocks. Once receive completion releases them, another request must progress.
    """
    vllm_config = create_vllm_config()
    block_size = vllm_config.cache_config.block_size
    scheduler = create_scheduler(vllm_config, num_blocks=6)  # five usable blocks
    block_pool = scheduler.kv_cache_manager.block_pool
    free_at_start = block_pool.get_num_free_blocks()
    remote = create_request(
        request_id=101,
        num_tokens=3 * block_size,
        block_size=block_size,
        do_remote_prefill=True,
        max_tokens=1,
    )
    waiting = create_request(
        request_id=102,
        num_tokens=4 * block_size,
        block_size=block_size,
        max_tokens=1,
    )
    scheduler.add_request(remote)
    scheduler.add_request(waiting)

    # Real admission reserves three blocks for the remote load. The four-block
    # local request cannot fit until that load relinquishes its allocation.
    output = scheduler.schedule()
    assert not output.num_scheduled_tokens
    assert remote.status == RequestStatus.WAITING_FOR_REMOTE_KVS
    assert remote in scheduler.kv_holding_waiting
    assert remote in scheduler.deferred_waiting
    remote_blocks = {
        block_id
        for group in scheduler.kv_cache_manager.get_block_ids(remote.request_id)
        for block_id in group
    }
    assert len(remote_blocks) == 3
    assert block_pool.get_num_free_blocks() == free_at_start - len(remote_blocks)
    scheduler.update_from_output(output, EMPTY_MODEL_RUNNER_OUTPUT)

    if receive_before_abort:
        output = scheduler.schedule()
        assert not output.num_scheduled_tokens
        scheduler.update_from_output(
            output,
            create_model_runner_output([], finished_recving={remote.request_id}),
        )
        assert remote.request_id in scheduler.finished_recving_kv_req_ids

    scheduler.finish_requests(remote.request_id, RequestStatus.FINISHED_ABORTED)
    assert scheduler.get_request_counts() == (0, 1)
    stats = scheduler.make_stats()
    assert stats is not None
    assert (stats.num_waiting_reqs, stats.num_skipped_waiting_reqs) == (1, 0)

    if not receive_before_abort:
        # Scheduler owns the deferred free even though the D-side connector's
        # request_finished hook does not itself request delayed release.
        assert remote.request_id in scheduler.requests
        assert block_pool.get_num_free_blocks() == free_at_start - len(remote_blocks)
        output = scheduler.schedule()
        assert not output.num_scheduled_tokens
        scheduler.update_from_output(output, EMPTY_MODEL_RUNNER_OUTPUT)
        output = scheduler.schedule()
        assert not output.num_scheduled_tokens
        scheduler.update_from_output(
            output,
            create_model_runner_output([], finished_recving={remote.request_id}),
        )

    assert remote.request_id not in scheduler.requests
    assert not scheduler.finished_recving_kv_req_ids
    assert block_pool.get_num_free_blocks() == free_at_start
    output = scheduler.schedule()
    assert set(output.num_scheduled_tokens) == {waiting.request_id}
    waiting_blocks = {
        block_id
        for group in scheduler.kv_cache_manager.get_block_ids(waiting.request_id)
        for block_id in group
    }
    assert remote_blocks & waiting_blocks
    completed = scheduler.update_from_output(
        output, create_model_runner_output([waiting], use_eos=True)
    )
    assert completed[0].outputs[0].request_id == waiting.request_id
    assert completed[0].outputs[0].finish_reason == FinishReason.STOP
    assert not scheduler.schedule().num_scheduled_tokens
    assert_scheduler_empty(scheduler)
