const { spawnSync } = require('child_process');

const data = {
  step: 'setup',
  data: {
    agent: 'antigravity',
    ide: 'vscode',
    mcpConfigured: false,
    skillsScope: 'project',
    mode: 'defaults',
    features: 'database'
  }
};

const args = ['neon@latest', 'init', '--agent', '--data', JSON.stringify(data)];
const result = spawnSync('npx.cmd', args, { stdio: 'inherit', shell: true });
if (result.error) {
  console.error('Failed:', result.error);
  process.exit(1);
}
process.exit(result.status);
