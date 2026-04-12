import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "视频变速管理台",
  description: "管理视频变速处理任务",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
