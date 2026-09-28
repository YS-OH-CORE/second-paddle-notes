export const identityCases = [
  { name: 'normal', identity: { name: 'identity-probe', version: '1.0.0' } },
  { name: 'empty-name', identity: { name: '', version: '1.0.0' } },
  { name: 'empty-version', identity: { name: 'identity-probe', version: '' } },
  { name: 'numeric-fields', identity: { name: 42, version: 7 } },
  { name: 'missing-fields', identity: {} }
];
