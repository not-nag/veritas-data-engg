export const metadata = { title: "Report · Veritas" };
import { ReportPage } from "@/components/report-page";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReportPage key={id} id={id} />;
}
