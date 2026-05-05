import { ConvexHttpClient } from 'convex/browser';
import { internal } from '../convex/_generated/api';

const url = process.env.CONVEX_URL;
if (!url) {
  console.error('CONVEX_URL env var required (e.g., the deployment URL)');
  process.exit(2);
}
const client = new ConvexHttpClient(url);

async function main() {
  const result = await client.mutation(internal.lib.migrate_v2.migrateAllToV2, {});
  console.log('migration result:', result);
  const ok =
    result.qInserted + result.qSkipped === result.qTotalSource &&
    result.dhPatched + result.dhSkipped === result.dhTotal;
  if (!ok) {
    console.error('MISMATCH: counts do not balance');
    process.exit(1);
  }
  console.log('OK');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
