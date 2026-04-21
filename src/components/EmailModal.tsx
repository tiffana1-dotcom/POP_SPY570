interface EmailModalProps {
  open: boolean;
  onClose: () => void;
  subject: string;
  body: string;
}

export function EmailModal({ open, onClose, subject, body }: EmailModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]"
        onClick={onClose}
        aria-label="Close dialog"
      />
      <div className="relative w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2
            id="email-modal-title"
            className="text-sm font-semibold text-slate-900"
          >
            Generated outreach email
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            <span className="sr-only">Close</span>
            ✕
          </button>
        </div>
        <div className="max-h-[min(70vh,520px)] overflow-y-auto px-5 py-4 space-y-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Subject
            </p>
            <p className="mt-1 text-sm text-slate-900">{subject}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Body
            </p>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm text-slate-800 leading-relaxed font-sans">
              {body}
            </pre>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4">
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard.writeText(`${subject}\n\n${body}`);
            }}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm hover:bg-slate-50"
          >
            Copy to clipboard
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
