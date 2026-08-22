import { BellOff } from "lucide-react";

import { SettingsPageTemplate } from "@/components/templates/settings-page-template";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

/**
 * Sprint 16 Session 4's architecture audit found no email provider, no
 * background job/scheduler, and no delivery path of any kind anywhere in
 * the backend (no Resend/SMTP, no Celery/Inngest, no queue) - the
 * Dashboard's "Alerts" widget is a live, pull-based query shown only while
 * a user is looking at the Dashboard, not something delivered to anyone.
 * With nothing that could actually send a notification, a preferences
 * toggle would control nothing real, so this page is deliberately a static
 * explanation rather than a form - Option C from the sprint's own
 * architecture-audit decision point, not a placeholder for missing work.
 */
export function NotificationPreferencesPage() {
  return (
    <SettingsPageTemplate
      title="Notification Preferences"
      description="What FishERP can notify you about today."
    >
      <Alert>
        <BellOff />
        <AlertTitle>Nothing to configure yet</AlertTitle>
        <AlertDescription>
          <p>
            FishERP doesn&apos;t send email, SMS, or push notifications to anyone yet, so there
            isn&apos;t a real preference to save here - a toggle would control nothing.
          </p>
          <p>
            The Dashboard&apos;s Alerts panel (overdue invoices and purchase bills, expiring boat
            licenses/insurance, stale drafts) is the closest thing that exists today, but it&apos;s
            computed live only while you&apos;re viewing the Dashboard - it isn&apos;t delivered to
            you, so there&apos;s nothing to turn on or off for it either.
          </p>
          <p>
            Once FishERP has a real delivery channel (email, for instance) and something that
            actually sends through it, this page will let you choose what you want to hear about.
          </p>
        </AlertDescription>
      </Alert>
    </SettingsPageTemplate>
  );
}
