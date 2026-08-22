import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { DecisionDrawerProvider } from "@/components/DecisionDrawer";
import { AccountProvider } from "@/components/Account";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "VeriFinder — Check before you decide", template: "%s — VeriFinder" },
  description: "Search companies and public records using verified data from official sources.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AccountProvider>
          <DecisionDrawerProvider>
            <Header />
            <main>{children}</main>
            <Footer />
          </DecisionDrawerProvider>
        </AccountProvider>
      </body>
    </html>
  );
}
