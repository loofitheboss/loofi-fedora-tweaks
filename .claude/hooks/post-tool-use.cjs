#!/usr/bin/env node

const { spawnSync } = require('node:child_process');

const filePath = process.env.CLAUDE_FILE_PATH || '';

if (!/\.py$/i.test(filePath)) {
  process.exit(0);
}

spawnSync(
  'flake8',
  [filePath, '--max-line-length=150', '--ignore=E501,W503,E402,E722,E203', '--quiet'],
  { stdio: 'ignore' },
);

process.exit(0);
