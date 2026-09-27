"""Characterize a documented tradeoff, not a new defect or model attack."""
from copy import deepcopy
import probe


def test_valid_v13_outputs_do_not_identify_original_image_ownership():
    """Two different tool-image assignments collapse to one valid history."""
    image_x = deepcopy(probe.IMAGE)
    image_y = {'type': 'image_url', 'image_url': {'url': 'https://example.invalid/second.png'}}
    split = probe.conversation([deepcopy(image_x)])
    split[3]['content'] = [deepcopy(image_y)]
    grouped = probe.conversation([deepcopy(image_x), deepcopy(image_y)])
    grouped[3]['content'] = []
    assert split != grouped
    split_before, grouped_before = deepcopy(split), deepcopy(grouped)
    split_v13, grouped_v13 = probe.adapt(split, 13), probe.adapt(grouped, 13)
    assert split_v13 == grouped_v13
    assert probe.check(split_v13, 13) == {'accepted': True}
    assert probe.check(grouped_v13, 13) == {'accepted': True}
    assert split_v13[-1]['content'] == [image_x, image_y]
    assert [m['tool_call_id'] for m in split_v13 if m['role'] == 'tool'] == ['abc123XYZ', 'def456UVW']
    assert probe.adapt(split, 15) is split
    assert probe.adapt(grouped, 15) is grouped
    assert probe.check(split, 15) == probe.check(grouped, 15) == {'accepted': True}
    assert split == split_before and grouped == grouped_before
