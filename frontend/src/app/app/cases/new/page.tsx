"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field } from "@/components/ui/Fields";
import { ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { Buyer, CaseCreate, CaseDetail, DealType } from "@/lib/api/types";
import { todayInIndia } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function NewDeliveryPage() {
  const router = useRouter();
  const buyers = useApiGet<Buyer[]>("/buyers");

  const [buyerId, setBuyerId] = useState("");
  const [newBuyer, setNewBuyer] = useState({ open: false, name: "", gstin: "" });
  const [buyerError, setBuyerError] = useState<ApiError | null>(null);
  const [form, setForm] = useState(() => ({
    invoiceNumber: "",
    invoiceDate: todayInIndia(),
    amount: "",
    deliveryDate: todayInIndia(),
    description: "",
    dealType: "verbal" as DealType,
    agreedDays: "",
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  if (buyers.error)
    return (
      <ErrorState
        message={buyers.error.message}
        requestId={buyers.error.requestId}
        onRetry={buyers.reload}
      />
    );
  if (!buyers.data) return <LoadingBlock label="Loading buyers" />;

  const selectedBuyer = buyerId || buyers.data[0]?.id || "";
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function addBuyer() {
    setBuyerError(null);
    try {
      const created = await api<Buyer>("/buyers", {
        method: "POST",
        json: { legal_name: newBuyer.name, gstin: newBuyer.gstin.trim() || null },
      });
      buyers.reload();
      setBuyerId(created.id);
      setNewBuyer({ open: false, name: "", gstin: "" });
    } catch (e) {
      setBuyerError(asApiError(e));
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const body: CaseCreate = {
      buyer_id: selectedBuyer,
      invoice_number: form.invoiceNumber,
      invoice_date: form.invoiceDate,
      invoice_amount: form.amount,
      delivery_date: form.deliveryDate,
      description: form.description.trim() || null,
      deal_type: form.dealType,
      agreed_payment_days:
        form.dealType === "written" && form.agreedDays !== "" ? Number(form.agreedDays) : null,
    };
    try {
      const created = await api<CaseDetail>("/cases", { method: "POST", json: body });
      router.push(`/app/cases/${created.id}`);
    } catch (e) {
      setError(asApiError(e));
      setSaving(false);
    }
  }

  const fieldError = (name: string) => error?.forField(name);
  const formLevelError = error && error.fieldErrors.length === 0 ? error.message : null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-h1 text-ink">Record delivery</h1>
        <p className="mt-1 text-small text-ink-muted">
          PaySetu starts the 15-day objection window from the delivery date and works out the dates
          from the rules.
        </p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-6" noValidate>
        {formLevelError ? (
          <Notice tone="danger" title="This delivery could not be saved">
            {formLevelError}
          </Notice>
        ) : null}
        {error && error.fieldErrors.length > 0 ? (
          <Notice tone="danger" title="Some fields need attention">
            {error.fieldErrors
              .map((e) => `${e.field.replace(/_/g, " ")}: ${e.message}`)
              .join(" · ")}
          </Notice>
        ) : null}

        <Card title="Buyer">
          <div className="flex flex-col gap-4">
            {buyers.data.length > 0 ? (
              <Field label="Buyer" required error={fieldError("buyer_id")}>
                {(control) => (
                  <select
                    {...control}
                    value={selectedBuyer}
                    onChange={(e) => setBuyerId(e.target.value)}
                    className={controlClass}
                  >
                    {buyers.data?.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.legal_name}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
            ) : (
              <p className="text-small text-ink-muted">No buyers yet. Add one to continue.</p>
            )}
            {newBuyer.open ? (
              <div className="flex flex-col gap-3 rounded-md bg-canvas p-4">
                <Field label="Buyer legal name" required error={buyerError?.forField("legal_name")}>
                  {(control) => (
                    <input
                      {...control}
                      value={newBuyer.name}
                      onChange={(e) => setNewBuyer({ ...newBuyer, name: e.target.value })}
                      className={controlClass}
                    />
                  )}
                </Field>
                <Field
                  label="Buyer GSTIN"
                  hint="Optional. 15 characters."
                  error={buyerError?.forField("gstin")}
                >
                  {(control) => (
                    <input
                      {...control}
                      value={newBuyer.gstin}
                      onChange={(e) => setNewBuyer({ ...newBuyer, gstin: e.target.value })}
                      className={`${controlClass} font-mono uppercase`}
                    />
                  )}
                </Field>
                {buyerError && buyerError.fieldErrors.length === 0 ? (
                  <Notice tone="danger">{buyerError.message}</Notice>
                ) : null}
                <div className="flex gap-2">
                  <Button onClick={addBuyer} disabled={!newBuyer.name.trim()}>
                    Save buyer
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setNewBuyer({ open: false, name: "", gstin: "" })}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="secondary"
                className="w-fit"
                onClick={() => setNewBuyer({ ...newBuyer, open: true })}
              >
                Add a buyer
              </Button>
            )}
          </div>
        </Card>

        <Card title="Invoice and delivery">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Invoice number" required error={fieldError("invoice_number")}>
              {(control) => (
                <input
                  {...control}
                  value={form.invoiceNumber}
                  onChange={(e) => set("invoiceNumber")(e.target.value)}
                  className={controlClass}
                  autoComplete="off"
                />
              )}
            </Field>
            <Field
              label="Invoice amount (Rs)"
              required
              error={fieldError("invoice_amount")}
              hint="Rupees, up to 2 decimals"
            >
              {(control) => (
                <input
                  {...control}
                  inputMode="decimal"
                  value={form.amount}
                  onChange={(e) => set("amount")(e.target.value)}
                  className={`${controlClass} tabular-nums`}
                  placeholder="500000.00"
                />
              )}
            </Field>
            <Field label="Invoice date" required error={fieldError("invoice_date")}>
              {(control) => (
                <input
                  {...control}
                  type="date"
                  value={form.invoiceDate}
                  onChange={(e) => set("invoiceDate")(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
            <Field
              label="Delivery date"
              required
              error={fieldError("delivery_date")}
              hint="Day 0 of the objection window"
            >
              {(control) => (
                <input
                  {...control}
                  type="date"
                  max={todayInIndia()}
                  value={form.deliveryDate}
                  onChange={(e) => set("deliveryDate")(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
          </div>
          <div className="mt-4">
            <Field label="Goods or services" error={fieldError("description")}>
              {(control) => (
                <input
                  {...control}
                  value={form.description}
                  onChange={(e) => set("description")(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
          </div>
        </Card>

        <Card title="Payment terms">
          <fieldset className="flex flex-col gap-3">
            <legend className="sr-only">Deal type</legend>
            {(
              [
                [
                  "verbal",
                  "Verbal or no written terms",
                  "Payment is due 15 days after acceptance under the Act.",
                ],
                [
                  "written",
                  "Written payment terms",
                  "An agreed period of up to 45 days from acceptance.",
                ],
              ] as const
            ).map(([value, title, body]) => (
              <label
                key={value}
                className={`flex cursor-pointer gap-3 rounded-md border p-3 ${
                  form.dealType === value ? "border-primary bg-primary-tint" : "border-rule-strong"
                }`}
              >
                <input
                  type="radio"
                  name="deal_type"
                  value={value}
                  checked={form.dealType === value}
                  onChange={() => setForm({ ...form, dealType: value })}
                  className="mt-1 size-4 accent-primary"
                />
                <span>
                  <span className="block text-body font-medium text-ink">{title}</span>
                  <span className="block text-small text-ink-muted">{body}</span>
                </span>
              </label>
            ))}
          </fieldset>
          {form.dealType === "written" ? (
            <div className="mt-4 max-w-xs">
              <Field
                label="Agreed payment period (days)"
                required
                error={fieldError("agreed_payment_days")}
                hint="Counted from acceptance. Periods over 45 days are capped at 45."
              >
                {(control) => (
                  <input
                    {...control}
                    inputMode="numeric"
                    value={form.agreedDays}
                    onChange={(e) => set("agreedDays")(e.target.value)}
                    className={`${controlClass} tabular-nums`}
                  />
                )}
              </Field>
            </div>
          ) : null}
        </Card>

        <div className="flex gap-3">
          <Button type="submit" loading={saving} disabled={!selectedBuyer}>
            Save delivery
          </Button>
          <Button variant="ghost" onClick={() => router.push("/app/cases")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
