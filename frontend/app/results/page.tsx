"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./page.module.css";

interface TokenInfo {
    address: string;
    symbol: string;
    name: string;
    type: string;
}

interface SpenderInfo {
    address: string;
    is_contract: boolean;
    name: string;
    verified: boolean;
}

interface Approval {
    token: TokenInfo;
    spender: SpenderInfo;
    approval_type: string;
    allowance: string;
    is_unlimited: boolean;
    age_days: number;
    risk_score: number;
    category: string;
    risk_reasons: string[];
    revoke_url: string;
    etherscan_url: string;
}

interface ScanResult {
    wallet: string;
    chain_id: number;
    hygiene_score: number;
    hygiene_label: string;
    summary: {
        total_approvals: number;
        dangerous: number;
        risky: number;
        safe: number;
    };
    approvals: {
        dangerous: Approval[];
        risky: Approval[];
        safe: Approval[];
    };
}

function ResultsContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [result, setResult] = useState<ScanResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"dangerous" | "risky" | "safe">("dangerous");

    const address = searchParams.get("address");
    const chainId = searchParams.get("chain") || "1";

    useEffect(() => {
        if (!address) {
            router.push("/");
            return;
        }

        const fetchResults = async () => {
            try {
                setLoading(true);
                const res = await fetch("/api/scan", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        address,
                        chain_id: parseInt(chainId)
                    }),
                });

                if (!res.ok) {
                    throw new Error("Scan failed");
                }

                const data = await res.json();
                setResult(data);

                // Set initial tab to first non-empty category
                if (data.approvals.dangerous.length > 0) {
                    setActiveTab("dangerous");
                } else if (data.approvals.risky.length > 0) {
                    setActiveTab("risky");
                } else {
                    setActiveTab("safe");
                }
            } catch (err) {
                setError("Failed to scan wallet. Please try again.");
            } finally {
                setLoading(false);
            }
        };

        fetchResults();
    }, [address, chainId, router]);

    if (loading) {
        return <LoadingState address={address || ""} />;
    }

    if (error || !result) {
        return <ErrorState error={error} onRetry={() => window.location.reload()} />;
    }

    const getScoreColor = (score: number) => {
        if (score >= 70) return "var(--safe)";
        if (score >= 40) return "var(--risky)";
        return "var(--danger)";
    };

    const circumference = 2 * Math.PI * 70;
    const scoreOffset = circumference - (result.hygiene_score / 100) * circumference;

    return (
        <main className={styles.main}>
            <div className={styles.container}>
                {/* Header */}
                <header className={styles.header}>
                    <Link href="/" className={styles.backLink}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M12 19l-7-7 7-7" />
                        </svg>
                        Back
                    </Link>
                    <div className={styles.walletAddress}>
                        {address?.slice(0, 6)}...{address?.slice(-4)}
                    </div>
                </header>

                {/* Score section */}
                <section className={styles.scoreSection}>
                    <div className={styles.scoreGauge}>
                        <svg viewBox="0 0 160 160" className={styles.scoreSvg}>
                            <circle
                                cx="80"
                                cy="80"
                                r="70"
                                className={styles.scoreCircleBg}
                            />
                            <circle
                                cx="80"
                                cy="80"
                                r="70"
                                className={styles.scoreCircleValue}
                                style={{
                                    strokeDasharray: circumference,
                                    strokeDashoffset: scoreOffset,
                                    stroke: getScoreColor(result.hygiene_score),
                                }}
                            />
                        </svg>
                        <div className={styles.scoreText}>
                            <span className={styles.scoreNumber}>{result.hygiene_score}</span>
                            <span className={styles.scoreLabel}>{result.hygiene_label}</span>
                        </div>
                    </div>

                    <div className={styles.scoreSummary}>
                        <h1>Wallet Hygiene Score</h1>
                        <p className={styles.summaryText}>
                            {result.summary.total_approvals === 0
                                ? "No active approvals found. Your wallet is clean!"
                                : `Found ${result.summary.total_approvals} active approval${result.summary.total_approvals !== 1 ? "s" : ""}`}
                        </p>
                        <div className={styles.stats}>
                            <div className={`${styles.stat} ${styles.statDanger}`}>
                                <span className={styles.statNumber}>{result.summary.dangerous}</span>
                                <span className={styles.statLabel}>Dangerous</span>
                            </div>
                            <div className={`${styles.stat} ${styles.statRisky}`}>
                                <span className={styles.statNumber}>{result.summary.risky}</span>
                                <span className={styles.statLabel}>Risky</span>
                            </div>
                            <div className={`${styles.stat} ${styles.statSafe}`}>
                                <span className={styles.statNumber}>{result.summary.safe}</span>
                                <span className={styles.statLabel}>Safe</span>
                            </div>
                        </div>
                    </div>
                </section>

                {/* What We Scanned section */}
                <section className={styles.scanInfoSection}>
                    <h2 className={styles.sectionTitle}>What We Analyzed</h2>
                    <div className={styles.scanInfoGrid}>
                        <div className={styles.scanInfoCard}>
                            <div className={styles.scanInfoIcon}>🔐</div>
                            <h3>Token Approvals</h3>
                            <p>Scanned ERC-20 token approvals that allow third parties to spend your tokens</p>
                        </div>
                        <div className={styles.scanInfoCard}>
                            <div className={styles.scanInfoIcon}>🖼️</div>
                            <h3>NFT Permissions</h3>
                            <p>Checked ERC-721 & ERC-1155 approvals including "Approval for All" permissions</p>
                        </div>
                        <div className={styles.scanInfoCard}>
                            <div className={styles.scanInfoIcon}>⚡</div>
                            <h3>Live Verification</h3>
                            <p>Verified current on-chain state to filter out already revoked permissions</p>
                        </div>
                        <div className={styles.scanInfoCard}>
                            <div className={styles.scanInfoIcon}>🎯</div>
                            <h3>Risk Analysis</h3>
                            <p>Scored each approval based on allowance size, spender type, and age</p>
                        </div>
                    </div>

                    <div className={styles.riskFactors}>
                        <h3>Risk Factors We Check</h3>
                        <div className={styles.factorsList}>
                            <div className={styles.factor}>
                                <span className={styles.factorWeight}>+40</span>
                                <span className={styles.factorName}>Unlimited Allowance</span>
                                <span className={styles.factorDesc}>Token can be drained completely</span>
                            </div>
                            <div className={styles.factor}>
                                <span className={styles.factorWeight}>+35</span>
                                <span className={styles.factorName}>EOA Spender</span>
                                <span className={styles.factorDesc}>Spender is a wallet, not a contract</span>
                            </div>
                            <div className={styles.factor}>
                                <span className={styles.factorWeight}>+25</span>
                                <span className={styles.factorName}>Approval For All</span>
                                <span className={styles.factorDesc}>Can transfer any NFT in collection</span>
                            </div>
                            <div className={styles.factor}>
                                <span className={styles.factorWeight}>+20</span>
                                <span className={styles.factorName}>Unverified Contract</span>
                                <span className={styles.factorDesc}>Source code not verified on explorer</span>
                            </div>
                            <div className={styles.factor}>
                                <span className={styles.factorWeight}>+15</span>
                                <span className={styles.factorName}>Old Approval</span>
                                <span className={styles.factorDesc}>Permission granted 6+ months ago</span>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Approvals section */}
                {result.summary.total_approvals > 0 && (
                    <section className={styles.approvalsSection}>
                        {/* Tabs */}
                        <div className={styles.tabs}>
                            <button
                                className={`${styles.tab} ${activeTab === "dangerous" ? styles.tabActive : ""} ${styles.tabDanger}`}
                                onClick={() => setActiveTab("dangerous")}
                                disabled={result.approvals.dangerous.length === 0}
                            >
                                🔴 Dangerous ({result.summary.dangerous})
                            </button>
                            <button
                                className={`${styles.tab} ${activeTab === "risky" ? styles.tabActive : ""} ${styles.tabRisky}`}
                                onClick={() => setActiveTab("risky")}
                                disabled={result.approvals.risky.length === 0}
                            >
                                🟡 Risky ({result.summary.risky})
                            </button>
                            <button
                                className={`${styles.tab} ${activeTab === "safe" ? styles.tabActive : ""} ${styles.tabSafe}`}
                                onClick={() => setActiveTab("safe")}
                                disabled={result.approvals.safe.length === 0}
                            >
                                🟢 Safe ({result.summary.safe})
                            </button>
                        </div>

                        {/* Approval cards */}
                        <div className={styles.approvalsList}>
                            {result.approvals[activeTab].map((approval, i) => (
                                <ApprovalCard key={i} approval={approval} />
                            ))}
                            {result.approvals[activeTab].length === 0 && (
                                <div className={styles.emptyState}>
                                    No {activeTab} approvals found
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* Share section */}
                <section className={styles.shareSection}>
                    <h3>Share your results</h3>
                    <button
                        className="btn btn-secondary"
                        onClick={() => {
                            const text = result.summary.dangerous > 0
                                ? `🚨 My wallet has ${result.summary.dangerous} dangerous approval(s)! Score: ${result.hygiene_score}/100. Check yours at RevokeMe`
                                : `✅ My wallet hygiene score: ${result.hygiene_score}/100. Check yours at RevokeMe`;
                            navigator.clipboard.writeText(text);
                        }}
                    >
                        📋 Copy to clipboard
                    </button>
                </section>
            </div>
        </main>
    );
}

function ApprovalCard({ approval }: { approval: Approval }) {
    return (
        <div className="approval-card">
            <div className="approval-header">
                <div className="token-info">
                    <div className="token-icon">
                        {approval.token.symbol?.slice(0, 2) || "??"}
                    </div>
                    <div>
                        <div className="token-name">{approval.token.symbol || "Unknown"}</div>
                        <div className="token-type">{approval.token.type}</div>
                    </div>
                </div>
                <span className={`badge badge-${approval.category}`}>
                    {approval.category}
                </span>
            </div>

            <div className="approval-details">
                <div className="detail-item">
                    <span className="detail-label">Allowance</span>
                    <span className={`detail-value ${approval.is_unlimited ? "unlimited" : ""}`}>
                        {approval.allowance}
                    </span>
                </div>
                <div className="detail-item">
                    <span className="detail-label">Spender</span>
                    <span className="detail-value">
                        {approval.spender.name ||
                            `${approval.spender.address.slice(0, 6)}...${approval.spender.address.slice(-4)}`}
                    </span>
                </div>
                <div className="detail-item">
                    <span className="detail-label">Age</span>
                    <span className="detail-value">
                        {approval.age_days > 0 ? `${approval.age_days} days` : "Recent"}
                    </span>
                </div>
                <div className="detail-item">
                    <span className="detail-label">Risk Score</span>
                    <span className="detail-value">{approval.risk_score}/100</span>
                </div>
            </div>

            {approval.risk_reasons.length > 0 && (
                <div className="risk-reasons">
                    {approval.risk_reasons.map((reason, i) => (
                        <span key={i} className="risk-tag">
                            ⚠️ {reason}
                        </span>
                    ))}
                </div>
            )}

            <div className="approval-actions">
                <a
                    href={approval.revoke_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-danger"
                >
                    Revoke on revoke.cash
                </a>
                <a
                    href={approval.etherscan_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                >
                    View on Etherscan
                </a>
            </div>
        </div>
    );
}

function LoadingState({ address }: { address: string }) {
    return (
        <main className={styles.main}>
            <div className={styles.loadingContainer}>
                <div className={styles.loadingSpinner} />
                <h2>Scanning wallet...</h2>
                <p className={styles.loadingAddress}>
                    {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : "Loading..."}
                </p>
                <div className={styles.loadingSteps}>
                    <div className={styles.loadingStep}>
                        <span className={styles.stepIcon}>🔍</span>
                        <span>Fetching ERC-20 approval events</span>
                    </div>
                    <div className={styles.loadingStep}>
                        <span className={styles.stepIcon}>🖼️</span>
                        <span>Scanning NFT permissions</span>
                    </div>
                    <div className={styles.loadingStep}>
                        <span className={styles.stepIcon}>⚡</span>
                        <span>Verifying current allowances on-chain</span>
                    </div>
                    <div className={styles.loadingStep}>
                        <span className={styles.stepIcon}>🎯</span>
                        <span>Calculating risk scores</span>
                    </div>
                </div>
                <p className={styles.loadingNote}>
                    This may take a few seconds depending on wallet activity
                </p>
            </div>
        </main>
    );
}

function ErrorState({
    error,
    onRetry
}: {
    error: string | null;
    onRetry: () => void;
}) {
    return (
        <main className={styles.main}>
            <div className={styles.errorContainer}>
                <div className={styles.errorIcon}>❌</div>
                <h2>Scan Failed</h2>
                <p>{error || "Something went wrong"}</p>
                <button className="btn btn-primary" onClick={onRetry}>
                    Try Again
                </button>
                <Link href="/" className="btn btn-secondary">
                    Go Back
                </Link>
            </div>
        </main>
    );
}

export default function ResultsPage() {
    return (
        <Suspense fallback={<LoadingState address="" />}>
            <ResultsContent />
        </Suspense>
    );
}
