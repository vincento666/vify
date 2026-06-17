import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'
import net from 'node:net'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendDir = resolve(__dirname, '../..')

export async function resolveFrontendServer() {
  const explicitBaseUrl = process.env.HIFY_E2E_BASE_URL || process.env.HIFY_FRONTEND_URL
  if (explicitBaseUrl) {
    return { baseUrl: trimTrailingSlash(explicitBaseUrl), close: async () => {} }
  }

  const host = process.env.HIFY_E2E_HOST || '127.0.0.1'
  const requestedPort = process.env.HIFY_E2E_FRONTEND_PORT || process.env.HIFY_FRONTEND_PORT || ''
  const port = requestedPort || String(await findFreePort(host))
  const baseUrl = `http://${host}:${port}`

  const child = spawn('npm', ['run', 'dev', '--', '--host', host, '--port', port, '--strictPort'], {
    cwd: frontendDir,
    env: {
      ...process.env,
      VITE_BACKEND_URL: process.env.VITE_BACKEND_URL || process.env.HIFY_BACKEND_URL || 'http://127.0.0.1:8000',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  const logs = []
  child.stdout.on('data', (chunk) => logs.push(String(chunk)))
  child.stderr.on('data', (chunk) => logs.push(String(chunk)))

  try {
    await waitUntilReachable(baseUrl, child, logs)
  } catch (error) {
    child.kill('SIGTERM')
    throw error
  }

  return {
    baseUrl,
    close: async () => {
      child.kill('SIGTERM')
      await delay(250)
    },
  }
}

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '')
}

async function isReachable(baseUrl) {
  try {
    const response = await fetch(baseUrl)
    return response.ok
  } catch {
    return false
  }
}

function findFreePort(host) {
  return new Promise((resolvePort, reject) => {
    const server = net.createServer()
    server.on('error', reject)
    server.listen(0, host, () => {
      const address = server.address()
      if (!address || typeof address !== 'object') {
        server.close(() => reject(new Error('Could not allocate a frontend e2e port')))
        return
      }
      const port = address.port
      server.close(() => resolvePort(port))
    })
  })
}

async function waitUntilReachable(baseUrl, child, logs) {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Vite dev server exited before ready.\n${logs.join('')}`)
    }
    if (await isReachable(baseUrl)) {
      return
    }
    await delay(250)
  }
  throw new Error(`Timed out waiting for Vite dev server at ${baseUrl}.\n${logs.join('')}`)
}
