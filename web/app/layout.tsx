import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Veritas · Operations",
  description: "Medical report standardisation and quality review",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
