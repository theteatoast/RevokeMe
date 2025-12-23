import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "RevokeMe - Wallet Approval Scanner",
    description: "Read-only security analysis tool that scans your wallet's token approvals and identifies risky permissions. No wallet connection required.",
    keywords: ["ethereum", "wallet", "security", "approvals", "tokens", "revoke", "permissions"],
    openGraph: {
        title: "RevokeMe - Wallet Approval Scanner",
        description: "Scan your wallet for risky token approvals. No signatures required.",
        type: "website",
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <head>
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
