import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "http://192.168.1.33:3000",
    "http://localhost:3000",
  ],
  // Sprint 18 Session 3: a production container only needs the traced
  // subset of node_modules `next build` determines this app actually uses
  // (output to .next/standalone), instead of shipping the full
  // node_modules tree - meaningful on a 1 vCPU / 6 GB VPS where image size
  // and container memory footprint both matter. No effect on `next dev`.
  output: "standalone",
};

export default nextConfig;