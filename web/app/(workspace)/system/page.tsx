export const metadata = { title: "System tools · Veritas" };
import { CloudPanel } from "@/components/cloud-panel";
import { OperationsPanel } from "@/components/operations-panel";
export default function Page() {
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>System tools</h1>
          <p>Recover failed files and manage automatic ingestion.</p>
        </div>
      </div>
      <OperationsPanel />
      <CloudPanel />
    </>
  );
}
