import { createClient } from '@supabase/supabase-js'

const url = process.env.SUPABASE_URL
const key = process.env.SUPABASE_ANON_KEY
const email = process.env.TEST_EMAIL
const password = process.env.TEST_PASSWORD
if (!url || !key || !email || !password) throw new Error('Missing env vars')

const supabase = createClient(url, key)

const { data: { user }, error: authErr } =
  await supabase.auth.signInWithPassword({ email, password })
if (authErr) throw authErr

const path = `${user.id}/demo.zip`
const file = new Blob(['hello-zip'], { type: 'application/zip' })

const up = await supabase.storage.from('artifacts').upload(path, file, { upsert: true })
console.log('storage:', up.error ?? 'ok')

const ins = await supabase.from('uploads').insert({
  owner: user.id, file_name: 'demo.zip', storage_path: `artifacts/${path}`
})
console.log('db insert:', ins.error ?? 'ok')