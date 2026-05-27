import { type FormEvent, type ReactNode, useMemo, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  CheckCircle2,
  FileText,
  Gavel,
  Layers3,
  Library,
  Link2,
  LoaderCircle,
  MessageCircle,
  MessagesSquare,
  Route,
  Scale,
  SearchCheck,
  SendHorizontal,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react"

import "./App.css"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type ConditionItem = {
  requirement?: string
  plain_explanation?: string
}

type RelatedBylaw = {
  section?: string | null
  subsection?: string | null
  title?: string | null
  score?: number | string | null
  statement?: string | null
  why_this_applies?: string | null
}

type RelatedRule = {
  section?: string | null
  subsection?: string | null
  title?: string | null
}

type AnalyzeResponse = {
  section?: string | null
  subsection?: string | null
  title?: string | null
  statement?: string
  explanation?: string
  why_this_applies?: string
  practical_guidance?: string
  citation?: string
  source_grounded_official_text?: string
  official_legal_text?: string
  official_excerpt?: string
  official_grounding_status?: string
  structured_specific_data?: Record<string, unknown> | unknown[]
  structured_legal_facts?: Record<string, unknown> | unknown[]
  conditions_required?: ConditionItem[]
  possible_challenges?: string[]
  related_statutes?: string[]
  related_rules?: RelatedRule[]
  related_bylaws?: RelatedBylaw[]
  confidence?: number
  confidence_label?: string
  disclaimer?: string
  success?: boolean
  message?: string
  match_type?: string
  needs_clarification?: boolean
  clarification_questions?: string[]
  possible_topics?: string[]
  when_may_not_apply?: string[]
  recommended_next_steps?: string[]
  documents_to_collect?: string[]
  possible_authorities?: string[]
}

type FollowupResponse = {
  answer?: string
  citation?: string
  confidence?: number
}

type StatusState = "idle" | "loading" | "success" | "error"

const examples = ["AGM quorum issue", "Sinking fund misuse", "Parking allocation", "Nominee transfer"]

const quickFacts = [
  { label: "Retrieval", value: "Hybrid + grounded" },
  { label: "Mode", value: "Informational" },
  { label: "Scope", value: "Maharashtra CHS" },
]

function asArray<T>(value: T[] | undefined | null): T[] {
  return Array.isArray(value) ? value : []
}

function percent(value?: number | string | null) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 0
  return Math.max(0, Math.min(100, Math.round(numeric * 100)))
}

function bylawLabel(result?: AnalyzeResponse | null) {
  if (!result?.section) return "Awaiting retrieval"
  return `Bye-law ${result.section}${result.subsection ? `(${result.subsection})` : ""}`
}

function officialText(result?: AnalyzeResponse | null) {
  return (
    result?.source_grounded_official_text ||
    result?.official_legal_text ||
    result?.official_excerpt ||
    result?.citation ||
    result?.statement ||
    "No official legal text was provided."
  )
}

function confidenceTone(value: number) {
  if (value >= 82) return "text-emerald-700 dark:text-emerald-300"
  if (value >= 60) return "text-blue-700 dark:text-blue-300"
  if (value >= 40) return "text-amber-700 dark:text-amber-300"
  return "text-zinc-600 dark:text-zinc-300"
}

function renderStructuredFacts(facts: AnalyzeResponse["structured_specific_data"] | AnalyzeResponse["structured_legal_facts"]) {
  if (!facts) return []
  if (Array.isArray(facts)) {
    return facts.map((item, index) => ({
      label: typeof item === "object" && item && "title" in item ? String(item.title) : `Fact ${index + 1}`,
      value: typeof item === "object" ? JSON.stringify(item) : String(item),
    }))
  }
  return Object.entries(facts)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => ({
      label: key.replaceAll("_", " "),
      value: typeof value === "object" ? JSON.stringify(value) : String(value),
    }))
}

function App() {
  const [description, setDescription] = useState("")
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [followup, setFollowup] = useState("")
  const [followupResult, setFollowupResult] = useState<FollowupResponse | null>(null)
  const [status, setStatus] = useState<StatusState>("idle")
  const [followupStatus, setFollowupStatus] = useState<StatusState>("idle")
  const [message, setMessage] = useState("")

  const confidence = percent(result?.confidence)
  const facts = useMemo(
    () => renderStructuredFacts(result?.structured_specific_data || result?.structured_legal_facts),
    [result?.structured_legal_facts, result?.structured_specific_data]
  )
  const relatedBylaws = asArray(result?.related_bylaws)
  const relatedRules = asArray(result?.related_rules)
  const conditions = asArray(result?.conditions_required)
  const challenges = asArray(result?.possible_challenges)
  const relatedStatutes = asArray(result?.related_statutes)
  const clarificationQuestions = asArray(result?.clarification_questions)

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const cleaned = description.trim()
    if (cleaned.length < 10) {
      setStatus("error")
      setMessage("Add a little more detail so the analyzer can identify the legal issue.")
      return
    }

    setStatus("loading")
    setMessage("Retrieving likely bye-laws...")
    setFollowup("")
    setFollowupResult(null)

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: cleaned }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.detail || "The analyzer could not process the request.")
      }

      const payload = (await response.json()) as AnalyzeResponse
      setResult(payload)
      setStatus("success")
      setMessage(payload.needs_clarification ? "Analysis ready. Clarification may improve precision." : "Analysis ready.")
    } catch (error) {
      setStatus("error")
      setMessage(error instanceof Error ? error.message : "Unexpected error while contacting the analyzer.")
    }
  }

  async function askFollowup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const question = followup.trim()
    if (!result) {
      setFollowupStatus("error")
      return
    }
    if (question.length < 2) {
      setFollowupStatus("error")
      return
    }

    setFollowupStatus("loading")
    try {
      const response = await fetch("/api/followup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, context: result }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.detail || "The follow-up request could not be processed.")
      }

      setFollowupResult((await response.json()) as FollowupResponse)
      setFollowupStatus("success")
    } catch {
      setFollowupStatus("error")
    }
  }

  return (
    <main className="min-h-screen bg-[var(--workspace-bg)] text-foreground">
      <div className="mx-auto grid w-[min(98vw,1760px)] gap-4 px-3 py-3 lg:grid-cols-[330px_minmax(0,1fr)_300px] xl:grid-cols-[360px_minmax(0,1fr)_320px]">
        <aside className="sticky top-3 self-start">
          <Card className="legal-surface min-h-[calc(100vh-24px)] justify-between border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-soft)]">
            <CardHeader className="gap-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                <p className="workspace-label">
                  <Scale className="size-3.5" />
                  Legal Situation Analyzer
                </p>
                <h1 className="mt-2 font-serif text-3xl leading-tight text-[var(--ink)]">Maharashtra society rule workspace</h1>
                <p className="mt-3 text-sm leading-6 text-[var(--muted-ink)]">
                  Describe the issue once. The workspace retrieves likely bye-laws, grounds the clause, and keeps follow-up questions close to the answer.
                </p>
                </div>
                <a
                  href="/"
                  className="inline-flex h-9 shrink-0 items-center rounded-lg border border-[var(--line)] bg-[var(--field)] px-3 text-xs font-semibold text-[var(--ink)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
                >
                  Classic UI
                </a>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              <form className="space-y-3" onSubmit={analyze}>
                <Textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="min-h-[210px] resize-y border-[var(--line)] bg-[var(--field)] p-3 text-sm leading-6 shadow-inner placeholder:text-[var(--muted-ink)]"
                  maxLength={3000}
                  placeholder="Example: Our AGM quorum was not complete, but the committee still passed decisions."
                />
                <div className="flex items-center gap-2">
                  <Button className="h-10 flex-1 bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)]" disabled={status === "loading"}>
                    {status === "loading" ? <LoaderCircle className="animate-spin" /> : <Sparkles />}
                    Analyze situation
                  </Button>
                  <Badge variant="outline" className={cn("h-10 rounded-lg px-3", status === "error" && "border-amber-400 text-amber-700")}>
                    {status === "idle" ? "Ready" : status}
                  </Badge>
                </div>
              </form>

              <div className="grid grid-cols-2 gap-2">
                {examples.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="rounded-lg border border-[var(--line)] bg-[var(--field)] px-3 py-2 text-left text-xs font-medium text-[var(--muted-ink)] transition hover:border-[var(--accent)] hover:text-[var(--ink)]"
                    onClick={() => setDescription(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </CardContent>

            <CardContent>
              <div className="grid gap-2 rounded-lg border border-[var(--line)] bg-[var(--field)] p-3">
                {quickFacts.map((item) => (
                  <div className="flex items-center justify-between gap-3 text-xs" key={item.label}>
                    <span className="text-[var(--muted-ink)]">{item.label}</span>
                    <span className="font-semibold text-[var(--ink)]">{item.value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </aside>

        <section className="min-w-0 space-y-4">
          <Card className="legal-surface overflow-visible border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-soft)]">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="workspace-label">
                    <SearchCheck className="size-3.5" />
                    Primary analysis
                  </p>
                  <CardTitle className="mt-1 font-serif text-2xl text-[var(--ink)]">Grounded legal reasoning</CardTitle>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="rounded-lg border-[var(--line)] bg-[var(--field)]">
                    Retrieval first
                  </Badge>
                  <Badge variant="outline" className="rounded-lg border-[var(--line)] bg-[var(--field)]">
                    Model bye-laws
                  </Badge>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-3">
              <AnimatePresence mode="wait">
                {status === "loading" ? (
                  <LoadingAnalysis key="loading" />
                ) : result ? (
                  <motion.div
                    key="result"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.24 }}
                    className="space-y-3"
                  >
                    <section className="layered-panel p-4">
                      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_230px]">
                        <div>
                          <p className="workspace-label">
                            <Gavel className="size-3.5" />
                            Applicable bye-law
                          </p>
                          <h2 className="mt-2 font-serif text-4xl leading-none text-[var(--ink)]">{bylawLabel(result)}</h2>
                          <p className="mt-2 text-sm font-semibold text-[var(--muted-ink)]">{result.title || "Rule title not identified"}</p>
                        </div>
                        <ConfidenceCard value={confidence} label={result.confidence_label} />
                      </div>

                      <div className="mt-4 grid gap-2 md:grid-cols-3">
                        {[
                          ["Retrieve", "Matched governing bye-law"],
                          ["Ground", result.official_grounding_status || "Official text checked"],
                          ["Explain", result.match_type || "Plain-language reasoning"],
                        ].map(([title, copy], index) => (
                          <motion.div
                            key={title}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.04 }}
                            className="rounded-lg border border-[var(--line)] bg-[var(--field)] p-3"
                          >
                            <span className="inline-flex size-6 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent)]">
                              {index + 1}
                            </span>
                            <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{title}</p>
                            <p className="mt-1 text-xs leading-5 text-[var(--muted-ink)]">{copy}</p>
                          </motion.div>
                        ))}
                      </div>

                      <div className="mt-4 rounded-lg border-l-4 border-[var(--accent)] bg-[var(--field)] p-3">
                        <p className="workspace-label">
                          <FileText className="size-3.5" />
                          Official legal text
                        </p>
                        <p className="mt-2 line-clamp-4 text-sm leading-6 text-[var(--ink)]">{officialText(result)}</p>
                      </div>
                    </section>

                    <section className="sticky top-3 z-10 rounded-xl border border-[var(--line)] bg-[color-mix(in_oklab,var(--surface)_90%,transparent)] p-3 shadow-[var(--shadow-soft)] backdrop-blur-xl">
                      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={askFollowup}>
                        <Textarea
                          value={followup}
                          onChange={(event) => setFollowup(event.target.value)}
                          className="min-h-11 flex-1 resize-none border-[var(--line)] bg-[var(--field)] px-3 py-2 text-sm"
                          placeholder="Ask a follow-up about this result..."
                        />
                        <Button className="h-11 bg-[var(--accent)] px-4 text-white hover:bg-[var(--accent-strong)]" disabled={!result || followupStatus === "loading"}>
                          {followupStatus === "loading" ? <LoaderCircle className="animate-spin" /> : <SendHorizontal />}
                          Ask
                        </Button>
                      </form>
                      {followupResult && (
                        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-3 rounded-lg border border-[var(--line)] bg-[var(--field)] p-3">
                          <p className="workspace-label">
                            <MessagesSquare className="size-3.5" />
                            Follow-up answer
                          </p>
                          <p className="mt-2 text-sm leading-6 text-[var(--ink)]">{followupResult.answer || "No answer was returned."}</p>
                        </motion.div>
                      )}
                    </section>

                    <Tabs defaultValue="meaning" className="space-y-3">
                      <TabsList className="grid h-auto w-full grid-cols-3 rounded-lg border border-[var(--line)] bg-[var(--field)] p-1">
                        <TabsTrigger value="meaning" className="h-9">Meaning</TabsTrigger>
                        <TabsTrigger value="details" className="h-9">Details</TabsTrigger>
                        <TabsTrigger value="related" className="h-9">Related</TabsTrigger>
                      </TabsList>
                      <TabsContent value="meaning" className="mt-0">
                        <div className="grid gap-3 lg:grid-cols-2">
                          <InsightCard icon={MessageCircle} title="Plain English" text={result.explanation || "No plain-English explanation was provided."} />
                          <InsightCard icon={Route} title="Practical guidance" text={result.practical_guidance || "Keep notices, minutes, receipts, emails, and society records before acting."} accent />
                        </div>
                      </TabsContent>
                      <TabsContent value="details" className="mt-0">
                        <Accordion type="multiple" className="rounded-xl border border-[var(--line)] bg-[var(--surface)]">
                          <DetailItem value="conditions" title="Conditions required" icon={CheckCircle2}>
                            <CompactGrid items={conditions.map((item) => ({ label: item.requirement || "Condition", value: item.plain_explanation || "No explanation provided." }))} />
                          </DetailItem>
                          <DetailItem value="challenges" title="Challenge arguments" icon={AlertTriangle}>
                            <BulletList items={challenges} fallback="No challenge arguments were returned." />
                          </DetailItem>
                          <DetailItem value="facts" title="Structured legal facts" icon={Library}>
                            <CompactGrid items={facts} />
                          </DetailItem>
                          <DetailItem value="limits" title="Limits and legal sources" icon={BookOpenText}>
                            <div className="grid gap-3 lg:grid-cols-2">
                              <BulletList items={asArray(result.when_may_not_apply)} fallback="No limits were returned." />
                              <BulletList items={relatedStatutes} fallback="No related statutes were returned." />
                            </div>
                          </DetailItem>
                        </Accordion>
                      </TabsContent>
                      <TabsContent value="related" className="mt-0">
                        <RelatedPanel relatedBylaws={relatedBylaws} relatedRules={relatedRules} />
                      </TabsContent>
                    </Tabs>

                    {result.needs_clarification && (
                      <Card className="border-amber-300/60 bg-amber-50/80 py-3 dark:border-amber-400/30 dark:bg-amber-500/10">
                        <CardContent className="space-y-2">
                          <p className="workspace-label text-amber-700 dark:text-amber-300">
                            <AlertTriangle className="size-3.5" />
                            Clarification can improve precision
                          </p>
                          <BulletList items={clarificationQuestions} fallback="Add more facts about the issue." />
                        </CardContent>
                      </Card>
                    )}
                  </motion.div>
                ) : (
                  <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid min-h-[430px] place-items-center rounded-xl border border-dashed border-[var(--line)] bg-[var(--field)] p-8 text-center">
                    <div>
                      <SearchCheck className="mx-auto size-9 text-[var(--accent)]" />
                      <h2 className="mt-4 font-serif text-3xl text-[var(--ink)]">Ready for legal retrieval</h2>
                      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[var(--muted-ink)]">
                        Your analysis will appear as a layered workspace with the primary bye-law, grounded text, guidance, and follow-up in one dense view.
                      </p>
                      {message && <p className="mt-4 text-sm text-[var(--muted-ink)]">{message}</p>}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>
        </section>

        <aside className="hidden space-y-4 xl:block">
          <Card className="legal-surface sticky top-3 border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-soft)]">
            <CardHeader>
              <p className="workspace-label">
                <Layers3 className="size-3.5" />
                Context panel
              </p>
              <CardTitle className="font-serif text-xl text-[var(--ink)]">Analysis map</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <ContextMetric label="Primary rule" value={result?.section ? bylawLabel(result) : "Not analyzed"} />
              <ContextMetric label="Confidence" value={result ? `${confidence}%` : "Pending"} />
              <ContextMetric label="Related rules" value={String(relatedBylaws.length || relatedRules.length || 0)} />
              <Separator />
              <div className="space-y-2">
                <p className="workspace-label">
                  <ShieldCheck className="size-3.5" />
                  Documents to keep
                </p>
                <BulletList items={asArray(result?.documents_to_collect)} fallback="Not available until analysis runs." />
              </div>
              <Separator />
              <div className="space-y-2">
                <p className="workspace-label">
                  <ArrowRight className="size-3.5" />
                  Next steps
                </p>
                <BulletList items={asArray(result?.recommended_next_steps)} fallback="Analyze a situation to see suggested next steps." />
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </main>
  )
}

function ConfidenceCard({ value, label }: { value: number; label?: string }) {
  return (
    <div className="grid grid-cols-[74px_1fr] items-center gap-3 rounded-xl border border-[var(--line)] bg-[var(--field)] p-3">
      <div
        className="grid size-[72px] place-items-center rounded-full"
        style={{
          background: `radial-gradient(circle at center, var(--surface) 0 56%, transparent 57%), conic-gradient(var(--accent) ${value}%, var(--ring-soft) 0)`,
        }}
      >
        <span className={cn("text-lg font-bold", confidenceTone(value))}>{value}%</span>
      </div>
      <div>
        <p className="workspace-label">Confidence</p>
        <p className="mt-1 text-sm font-bold text-[var(--ink)]">{label || "Match score"}</p>
        <p className="mt-1 text-xs leading-5 text-[var(--muted-ink)]">
          {value >= 60 ? "Relevant enough to review first." : "Useful but facts may be incomplete."}
        </p>
      </div>
    </div>
  )
}

function LoadingAnalysis() {
  return (
    <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
      <section className="layered-panel p-4">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_230px]">
          <div className="space-y-3">
            <div className="h-3 w-28 rounded-full bg-[var(--skeleton)]" />
            <div className="h-10 w-64 rounded-lg bg-[var(--skeleton)]" />
            <div className="h-4 w-80 max-w-full rounded-full bg-[var(--skeleton)]" />
          </div>
          <div className="h-28 rounded-xl bg-[var(--skeleton)]" />
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {["Retrieving", "Grounding", "Explaining"].map((item) => (
            <div className="rounded-lg border border-[var(--line)] bg-[var(--field)] p-3" key={item}>
              <LoaderCircle className="size-4 animate-spin text-[var(--accent)]" />
              <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{item}</p>
              <div className="mt-2 h-3 rounded-full bg-[var(--skeleton)]" />
            </div>
          ))}
        </div>
      </section>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="h-36 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <div className="h-3 w-24 rounded-full bg-[var(--skeleton)]" />
          <div className="mt-5 h-3 rounded-full bg-[var(--skeleton)]" />
          <div className="mt-3 h-3 w-2/3 rounded-full bg-[var(--skeleton)]" />
        </div>
        <div className="h-36 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <div className="h-3 w-24 rounded-full bg-[var(--skeleton)]" />
          <div className="mt-5 h-3 rounded-full bg-[var(--skeleton)]" />
          <div className="mt-3 h-3 w-2/3 rounded-full bg-[var(--skeleton)]" />
        </div>
      </div>
    </motion.div>
  )
}

function InsightCard({ icon: Icon, title, text, accent = false }: { icon: LucideIcon; title: string; text: string; accent?: boolean }) {
  return (
    <motion.article initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-[var(--shadow-soft)]", accent && "bg-[var(--success-soft)]")}>
      <p className="workspace-label">
        <Icon className="size-3.5" />
        {title}
      </p>
      <p className="mt-3 text-sm leading-6 text-[var(--ink)]">{text}</p>
    </motion.article>
  )
}

function DetailItem({ value, title, icon: Icon, children }: { value: string; title: string; icon: LucideIcon; children: ReactNode }) {
  return (
    <AccordionItem value={value} className="border-[var(--line)] px-3">
      <AccordionTrigger className="hover:no-underline">
        <span className="inline-flex items-center gap-2">
          <Icon className="size-4 text-[var(--accent)]" />
          {title}
        </span>
      </AccordionTrigger>
      <AccordionContent>{children}</AccordionContent>
    </AccordionItem>
  )
}

function CompactGrid({ items }: { items: { label: string; value: string }[] }) {
  if (!items.length) return <p className="text-sm text-[var(--muted-ink)]">No structured details were returned.</p>
  return (
    <div className="grid gap-2 md:grid-cols-2">
      {items.map((item, index) => (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--field)] p-3" key={`${item.label}-${index}`}>
          <p className="text-xs font-bold capitalize text-[var(--ink)]">{item.label}</p>
          <p className="mt-1 text-xs leading-5 text-[var(--muted-ink)]">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

function BulletList({ items, fallback }: { items: string[]; fallback: string }) {
  if (!items.length) return <p className="text-sm leading-6 text-[var(--muted-ink)]">{fallback}</p>
  return (
    <ul className="space-y-2">
      {items.slice(0, 6).map((item, index) => (
        <li className="flex gap-2 text-sm leading-6 text-[var(--muted-ink)]" key={`${item}-${index}`}>
          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--accent)]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function RelatedPanel({ relatedBylaws, relatedRules }: { relatedBylaws: RelatedBylaw[]; relatedRules: RelatedRule[] }) {
  const items = relatedBylaws.length
    ? relatedBylaws.map((item) => ({
        code: `Bye-law ${item.section || ""}${item.subsection ? `(${item.subsection})` : ""}`,
        title: item.title || "Related bye-law",
        score: percent(item.score),
        statement: item.statement || item.why_this_applies || "",
      }))
    : relatedRules.map((item) => ({
        code: `${item.section || ""}${item.subsection ? `(${item.subsection})` : ""}`,
        title: item.title || "Related rule",
        score: 0,
        statement: "",
      }))

  if (!items.length) return <Card className="border-[var(--line)] bg-[var(--surface)]"><CardContent>No related bye-laws were returned.</CardContent></Card>

  return (
    <div className="grid gap-2 lg:grid-cols-2">
      {items.map((item, index) => (
        <motion.article
          key={`${item.code}-${index}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.04 }}
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3 shadow-[var(--shadow-soft)]"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="inline-flex items-center gap-2 text-sm font-bold text-[var(--ink)]">
              <Link2 className="size-4 text-[var(--accent)]" />
              {item.code}
            </p>
            {item.score > 0 && <Badge variant="outline" className="rounded-lg">{item.score}%</Badge>}
          </div>
          <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{item.title}</p>
          {item.statement && <p className="mt-2 line-clamp-3 text-xs leading-5 text-[var(--muted-ink)]">{item.statement}</p>}
        </motion.article>
      ))}
    </div>
  )
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[var(--line)] bg-[var(--field)] px-3 py-2">
      <span className="text-xs text-[var(--muted-ink)]">{label}</span>
      <span className="text-right text-xs font-bold text-[var(--ink)]">{value}</span>
    </div>
  )
}

export default App
