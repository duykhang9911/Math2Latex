import { cpSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = dirname(dirname(fileURLToPath(import.meta.url)))
const source = join(projectRoot, 'node_modules', 'mathlive', 'fonts')
const destination = join(projectRoot, 'public', 'mathlive-fonts')

mkdirSync(destination, { recursive: true })
cpSync(source, destination, { recursive: true, force: true })