import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "ContentPilot — Self-Evaluating Agentic RAG System",
  description: "Enterprise self-evaluating content generation system with 4-layer gates and pgvector.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#0b0d17] text-slate-100 antialiased selection:bg-purple-500 selection:text-white">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
          {children}
        </main>
        <footer className="border-t border-white/10 py-6 text-center text-xs text-slate-500">
          ContentPilot Enterprise Agentic Architecture • Powered by FastAPI & Next.js Standard
        </footer>
      </body>
    </html>
  );
}
