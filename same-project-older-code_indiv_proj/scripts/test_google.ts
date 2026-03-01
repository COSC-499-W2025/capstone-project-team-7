import { env } from '../src/config/env';
import services from '../src/services';

async function run() {
  console.log('env.USE_MOCK_SERVICES=', env.USE_MOCK_SERVICES);
  if (env.USE_MOCK_SERVICES) {
    console.error('USE_MOCK_SERVICES is true — set USE_MOCK_SERVICES=false to test real Google APIs');
    process.exit(2);
  }

  if (!process.env.SPREADSHEET_ID) {
    console.error('Missing SPREADSHEET_ID env');
    process.exit(2);
  }

  const { drive, sheets } = services as any;

  try {
    console.log('Attempting to append a test row to spreadsheet:', process.env.SPREADSHEET_ID);
    await sheets.appendRow(process.env.SPREADSHEET_ID!, [new Date().toISOString(), 'ankas-agent-test', 'ok']);
    console.log('Appended test row to spreadsheet');
  } catch (e: any) {
    console.error('Failed to append row:', e && e.message ? e.message : e);
    process.exit(3);
  }

  try {
    console.log('Attempting to upload a small test file to Drive');
    const res = await drive.upload(Buffer.from('ankas-agent test'), `ankas-agent-test-${Date.now()}.txt`);
    console.log('Uploaded file to Drive:', res);
  } catch (e: any) {
    console.error('Failed to upload to Drive:', e && e.message ? e.message : e);
    process.exit(4);
  }

  console.log('Google Drive/Sheets test completed successfully');
}

run().catch((err) => {
  console.error('Unexpected error', err);
  process.exit(10);
});
