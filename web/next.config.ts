import type { NextConfig } from "next";
const config: NextConfig = {
  devIndicators: false,
  headers() {
    return ["walkthrough-example.json", "walkthrough-invalid.json"].map(
      (name) => ({
        source: "/" + name,
        headers: [
          {
            key: "Content-Disposition",
            value: `attachment; filename="${name}"`,
          },
        ],
      }),
    );
  },
};
export default config;
