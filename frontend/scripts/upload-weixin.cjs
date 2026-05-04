const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const bundledNode = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
const nodeMajor = Number(process.versions.node.split('.')[0])
if (nodeMajor >= 25 && !process.env.MP_WEIXIN_NO_REEXEC && fs.existsSync(bundledNode)) {
  const result = spawnSync(bundledNode, [__filename, ...process.argv.slice(2)], {
    stdio: 'inherit',
    env: { ...process.env, MP_WEIXIN_NO_REEXEC: '1' },
  })
  process.exit(result.status || 0)
}

const ci = require('miniprogram-ci')

const rootDir = path.resolve(__dirname, '..')
const pkg = require(path.join(rootDir, 'package.json'))
const projectPath = path.resolve(rootDir, process.env.MP_WEIXIN_PROJECT_PATH || 'dist/build/mp-weixin')
const projectConfigPath = path.join(projectPath, 'project.config.json')
const projectConfig = fs.existsSync(projectConfigPath) ? require(projectConfigPath) : {}
const appid = process.env.MP_WEIXIN_APPID || projectConfig.appid || 'wx2e1ef8d44ff1dc09'
const privateKeyPath = process.env.MP_WEIXIN_PRIVATE_KEY_PATH || path.join(os.homedir(), 'Downloads/private.wx2e1ef8d44ff1dc09.key')
const version = process.env.MP_WEIXIN_VERSION || pkg.version || '0.1.0'
const desc = process.env.MP_WEIXIN_DESC || `MioDraw AI 绘图小程序 ${version}`
const robot = Number(process.env.MP_WEIXIN_ROBOT || 1)

function requireFile(filePath, label) {
  if (!fs.existsSync(filePath)) {
    console.error(`${label} 不存在：${filePath}`)
    process.exit(1)
  }
}

async function main() {
  requireFile(projectConfigPath, '小程序构建配置')
  requireFile(privateKeyPath, '微信小程序上传密钥')

  const project = new ci.Project({
    appid,
    type: 'miniProgram',
    projectPath,
    privateKeyPath,
    ignores: ['node_modules/**/*'],
  })

  console.log(`上传微信小程序：appid=${appid}, version=${version}, robot=${robot}`)
  console.log(`项目目录：${projectPath}`)

  const result = await ci.upload({
    project,
    version,
    desc,
    robot,
    setting: {
      useProjectConfig: true,
    },
    onProgressUpdate: (event) => {
      if (typeof event === 'string') console.log(event)
      else if (event && event.message) console.log(event.message)
    },
  })

  console.log('微信小程序上传完成')
  if (result) console.log(JSON.stringify(result, null, 2))
}

main().catch((error) => {
  console.error(error && error.message ? error.message : error)
  process.exit(1)
})
