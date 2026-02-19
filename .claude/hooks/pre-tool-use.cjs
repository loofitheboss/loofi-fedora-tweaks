#!/usr/bin/env node

const filePath = (process.env.CLAUDE_FILE_PATH || '').toLowerCase();

const isSecretPath = /\.(env|secret|key)$/.test(filePath) || /(^|[\\/])mcp\.env$/.test(filePath);

if (isSecretPath) {
  console.error('BLOCKED: Cannot edit secrets/env files');
  process.exit(1);
}

process.exit(0);
