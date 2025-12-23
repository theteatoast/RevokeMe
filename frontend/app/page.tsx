"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

export default function Home() {
    const router = useRouter();
    const [address, setAddress] = useState("");
    const [isValidating, setIsValidating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const validateAddress = (addr: string): boolean => {
        const regex = /^0x[a-fA-F0-9]{40}$/;
        return regex.test(addr);
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        const trimmed = address.trim();

        if (!trimmed) {
            setError("Please enter a wallet address");
            return;
        }

        if (!validateAddress(trimmed)) {
            setError("Invalid Ethereum address format");
            return;
        }

        setIsValidating(true);

        try {
            // Validate with backend
            const res = await fetch("/api/validate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ address: trimmed }),
            });

            const data = await res.json();

            if (!data.valid) {
                setError(data.error || "Invalid address");
                setIsValidating(false);
                return;
            }

            // Navigate to results page
            router.push(`/results?address=${data.checksum || trimmed}&chain=1`);
        } catch (err) {
            // If backend is not available, proceed anyway
            router.push(`/results?address=${trimmed}&chain=1`);
        }
    };

    return (
        <main className={styles.main}>
            <div className={styles.hero}>
                {/* Logo/branding */}
                <div className={styles.logoContainer}>
                    <div className={styles.logo}>
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                            <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                            <circle cx="24" cy="24" r="12" stroke="currentColor" strokeWidth="2" />
                            <path d="M24 16V24L30 30" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        </svg>
                    </div>
                    <span className={styles.logoText}>RevokeMe</span>
                </div>

                {/* Headline */}
                <h1 className={styles.title}>
                    Scan your wallet for
                    <br />
                    <span className={styles.gradient}>risky approvals</span>
                </h1>

                <p className={styles.subtitle}>
                    Find unlimited allowances, unknown spenders, and dormant permissions
                    <br />
                    that could drain your wallet.
                </p>

                {/* Search form */}
                <form onSubmit={handleSubmit} className={styles.searchForm}>
                    <div className={styles.inputWrapper}>
                        <input
                            type="text"
                            value={address}
                            onChange={(e) => {
                                setAddress(e.target.value);
                                setError(null);
                            }}
                            placeholder="Enter wallet address (0x...)"
                            className={`input ${styles.searchInput} ${error ? styles.inputError : ""}`}
                            spellCheck={false}
                            autoComplete="off"
                        />
                        <button
                            type="submit"
                            disabled={isValidating}
                            className={`btn btn-primary ${styles.scanButton}`}
                        >
                            {isValidating ? (
                                <>
                                    <span className="spinner" />
                                    Validating
                                </>
                            ) : (
                                <>
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="11" cy="11" r="8" />
                                        <path d="M21 21l-4.35-4.35" />
                                    </svg>
                                    Scan
                                </>
                            )}
                        </button>
                    </div>

                    {error && <p className={styles.error}>{error}</p>}
                </form>

                {/* Trust message */}
                <p className={styles.trustMessage}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        <path d="M9 12l2 2 4-4" />
                    </svg>
                    We never ask for signatures. Read-only scan.
                </p>

                {/* Features */}
                <div className={styles.features}>
                    <div className={styles.feature}>
                        <div className={styles.featureIcon}>🔍</div>
                        <h3>Scan Approvals</h3>
                        <p>ERC20, ERC721, ERC1155</p>
                    </div>
                    <div className={styles.feature}>
                        <div className={styles.featureIcon}>⚠️</div>
                        <h3>Identify Risks</h3>
                        <p>Unlimited & stale permissions</p>
                    </div>
                    <div className={styles.feature}>
                        <div className={styles.featureIcon}>🔗</div>
                        <h3>Revoke Easily</h3>
                        <p>Direct links to revoke</p>
                    </div>
                </div>
            </div>
        </main>
    );
}
