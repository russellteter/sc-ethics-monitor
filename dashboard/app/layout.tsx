import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SC House Dem Finance — Locality AI",
  description:
    "Q1 quarterly campaign-finance disclosures for Democrat SC State House candidates.",
  icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }] },
  openGraph: { images: ["/og.png"] },
};

const fonts = (
  <link
    rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Syne:wght@500;700;800&family=Inter:wght@400;500;600&display=swap"
  />
);

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>{fonts}</head>
      <body>{children}</body>
    </html>
  );
}
