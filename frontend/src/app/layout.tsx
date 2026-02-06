import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Taskio Pro | AI Ticket Classification",
  description: "Enterprise AI-powered support ticket classification with LangChain & RAG",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100 antialiased">
        {children}
      </body>
    </html>
  );
}
