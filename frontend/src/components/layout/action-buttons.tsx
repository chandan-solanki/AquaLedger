import type { VariantProps } from "class-variance-authority";
import type { LucideIcon } from "lucide-react";

import { Button, type buttonVariants } from "@/components/ui/button";

type BaseButtonProps = Omit<React.ComponentProps<typeof Button>, "variant">;

/** The single main action on a page/dialog — fixed to the Primary Button variant, per `06_COMPONENT_LIBRARY.md` §3. */
export function PrimaryActionButton(props: BaseButtonProps) {
  return <Button variant="default" {...props} />;
}

/** Supporting, non-destructive actions beside a Primary Button — fixed to the Outline variant. */
export function SecondaryActionButton(props: BaseButtonProps) {
  return <Button variant="outline" {...props} />;
}

/** Reserved exclusively for destructive/irreversible actions — fixed to the Danger (destructive) variant, per `06_COMPONENT_LIBRARY.md` §3. Always pair with a `ConfirmationDialog`. */
export function DangerActionButton(props: BaseButtonProps) {
  return <Button variant="destructive" {...props} />;
}

/** A lighter-weight, compact action for toolbars (List page Toolbar, Table Toolbar) where several actions coexist without one dominating. */
export function ToolbarButton(props: BaseButtonProps & Pick<VariantProps<typeof buttonVariants>, "size">) {
  return <Button variant="outline" size="sm" {...props} />;
}

interface IconActionButtonProps extends Omit<BaseButtonProps, "children" | "size"> {
  icon: LucideIcon;
  /** Required even though the button is visually icon-only, per `06_COMPONENT_LIBRARY.md` §3 / `02_DESIGN_SYSTEM.md` §7. */
  label: string;
  size?: "icon" | "icon-sm" | "icon-lg";
}

/** A square, icon-only button for well-established, unambiguous actions (close, kebab, refresh) — always carries an accessible label. */
export function IconActionButton({ icon: Icon, label, size = "icon-sm", ...props }: IconActionButtonProps) {
  return (
    <Button variant="ghost" size={size} aria-label={label} {...props}>
      <Icon aria-hidden />
    </Button>
  );
}
