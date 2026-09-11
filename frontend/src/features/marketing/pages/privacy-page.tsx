import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { SITE_NAME, SUPPORT_EMAIL } from "@/lib/site-config";

const LAST_UPDATED = "September 11, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <div className="space-y-3 text-sm text-muted-foreground">{children}</div>
    </section>
  );
}

export function PrivacyPage() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="border-b">
        <div className="mx-auto flex w-full max-w-3xl items-center px-6 py-4">
          <Button asChild variant="ghost" size="sm">
            <Link href="/">
              <ArrowLeft />
              Back to {SITE_NAME}
            </Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl space-y-10 px-6 py-12">
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              {SITE_NAME} Privacy Policy
            </h1>
            <p className="text-sm text-muted-foreground">Last updated: {LAST_UPDATED}</p>
            <p className="text-sm text-muted-foreground">
              This is an application privacy policy describing how {SITE_NAME} — a business
              management (ERP) system for seafood trading and fishing operations — handles data
              for the organizations and users that operate it. It is not a substitute for legal
              advice, and it does not constitute a claim of compliance with any specific law or
              certification unless explicitly stated below.
            </p>
          </div>

          <Section title="1. Information we collect">
            <p>Depending on how {SITE_NAME} is used, the application may hold:</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>
                <strong>Account information</strong> — name, email address, phone number, and role
                assignments for users who log in.
              </li>
              <li>
                <strong>Business and company records</strong> you or your organization enter —
                customer/company details, fish master data, boats, trips and catches, invoices,
                payments, purchase bills, and expenses.
              </li>
              <li>
                <strong>Documents you upload</strong> — files such as receipts or contracts that
                you attach to a business record.
              </li>
              <li>
                <strong>Audit information</strong> — a record of who performed which action on
                which record and when, kept for accountability of business and financial records.
              </li>
              <li>
                <strong>Technical and log information</strong> — data such as login timestamps, IP
                address, and browser/user-agent information associated with requests to the
                application.
              </li>
            </ul>
          </Section>

          <Section title="2. How we use this information">
            <ul className="list-disc space-y-1 pl-5">
              <li>To provide and operate the {SITE_NAME} service.</li>
              <li>To authenticate users and enforce role-based access permissions.</li>
              <li>To maintain business and financial records you create in the system.</li>
              <li>To generate reports you request.</li>
              <li>For security monitoring and audit purposes.</li>
              <li>For backups and disaster recovery, so business records are not lost.</li>
              <li>To operate, maintain, and troubleshoot the service.</li>
            </ul>
          </Section>

          <Section title="3. Data storage">
            <p>
              Business data you enter into {SITE_NAME} — companies, invoices, payments, trips, and
              related records — is stored in a database operated as part of the {SITE_NAME}
              application infrastructure. Documents you upload are stored in file storage that is
              part of the same infrastructure. We do not sell or share this data with third
              parties for advertising or marketing purposes.
            </p>
          </Section>

          <Section title="4. Backups">
            <p>
              Database backups are created on a regular schedule and stored in secured, access-
              controlled off-site storage, separate from the primary application server, so
              business records can be recovered in the event of a failure. One backup copy is
              encrypted before it leaves our infrastructure. As part of this process, backups may
              be stored using a third-party cloud storage provider (Google Drive). We do not
              disclose encryption keys, credentials, or other infrastructure configuration in this
              policy or elsewhere publicly.
            </p>
          </Section>

          <Section title="5. Security">
            <p>The following protections are in place today:</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>The application is served over an encrypted HTTPS connection.</li>
              <li>User passwords are never stored in plain text — they are hashed using Argon2id.</li>
              <li>
                Authentication uses short-lived session tokens with a separate, revocable refresh
                mechanism.
              </li>
              <li>Access to business data is governed by role-based access control (RBAC).</li>
              <li>Off-site database backups include an encrypted copy, and backup files are kept under restricted, access-controlled storage.</li>
            </ul>
            <p>
              We do not claim certification against any specific security or compliance standard
              (for example, ISO 27001, SOC 2, or GDPR) unless a certificate or attestation is
              published separately.
            </p>
          </Section>

          <Section title="6. Data retention">
            <p>
              Issued invoices and ledger entries are part of the permanent business/financial
              record and are not deleted; corrections are made through credit notes or reversing
              entries rather than by altering history. We have not defined a fixed general
              retention period for account or business data beyond what is needed to operate the
              service. Off-site backups are retained on a rolling schedule (currently the most
              recent several weekly backups at each backup location) and older backups are removed
              as newer ones are confirmed successful.
            </p>
          </Section>

          <Section title="7. Your rights and requests">
            <p>
              If you have questions about your data, or would like to request access to or
              correction of information held about you, contact us at{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="font-medium text-foreground underline underline-offset-4"
              >
                {SUPPORT_EMAIL}
              </a>
              .
            </p>
          </Section>

          <Section title="8. Third-party services">
            <p>
              We use a third-party cloud storage provider (Google Drive) solely to store encrypted
              and access-controlled off-site database backups for disaster recovery. This service
              is not used to collect or process end-user data submitted through the application
              itself, and no application credentials or OAuth tokens are disclosed publicly.
            </p>
          </Section>

          <Section title="9. Changes to this policy">
            <p>
              We may update this policy as the application or our practices change. The
              &ldquo;Last updated&rdquo; date above reflects the most recent revision.
            </p>
          </Section>

          <Section title="10. Contact">
            <p>
              For any privacy-related questions about {SITE_NAME}, contact{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="font-medium text-foreground underline underline-offset-4"
              >
                {SUPPORT_EMAIL}
              </a>
              .
            </p>
          </Section>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}
