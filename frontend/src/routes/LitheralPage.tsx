import { useEffect, useState } from "react";
import { TierGate } from "../components/TierGate";
import { UpgradePrompt } from "../components/UpgradePrompt";
import {
  listStudyPlan, generateStudyPlan, regenerateStudyBlock,
  listMyTimetable, listRoutines, generateLifeSchedule, listLifeSchedule, getAiUsage
} from "../lib/api/endpoints";
import type { StudyBlockPublic, LifeBlockPublic, RoutinePublic, UsageStatusResponse } from "../lib/api/types";
import { isApiError } from "../lib/api/errors";
import { StudyPlanConfig } from "../components/StudyPlanConfig";
import { RoutineEditor } from "../components/RoutineEditor";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function LitheralPage() {
  const [tab, setTab] = useState<"study" | "life">("study");
  const [studyPlan, setStudyPlan] = useState<StudyBlockPublic[] | null>(null);
  const [lifeSchedule, setLifeSchedule] = useState<LifeBlockPublic[] | null>(null);
  const [routines, setRoutines] = useState<RoutinePublic[] | null>(null);
  const [timetableSubjects, setTimetableSubjects] = useState<string[]>([]);
  const [usage, setUsage] = useState<UsageStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sp, tt, usageData] = await Promise.all([
        listStudyPlan(),
        listMyTimetable(),
        getAiUsage()
      ]);
      setStudyPlan(sp);
      setUsage(usageData);

      const subjects = Array.from(new Set(tt.map(e => e.subject)));
      setTimetableSubjects(subjects);

      if (tab === "life") {
        const [ls, rt] = await Promise.all([listLifeSchedule(), listRoutines()]);
        setLifeSchedule(ls);
        setRoutines(rt);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [tab]);

  async function handleGenerateStudy(subjects: any) {
    setSubmitting(true);
    try {
      const plan = await generateStudyPlan(subjects);
      setStudyPlan(plan);
      const usageData = await getAiUsage();
      setUsage(usageData);
    } catch (err) {
      alert(isApiError(err) ? err.message : "Generation failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegenerateBlock(id: string) {
    try {
      const res = await regenerateStudyBlock(id);
      setStudyPlan(prev => prev?.map(b => b.id === res.block.id ? res.block : b) || null);
      const usageData = await getAiUsage();
      setUsage(usageData);
    } catch (err) {
      alert(isApiError(err) ? err.message : "Regeneration failed");
    }
  }

  async function handleGenerateLife() {
    setSubmitting(true);
    try {
      const schedule = await generateLifeSchedule();
      setLifeSchedule(schedule);
      const usageData = await getAiUsage();
      setUsage(usageData);
    } catch (err) {
      alert(isApiError(err) ? err.message : "Generation failed");
    } finally {
      setSubmitting(false);
    }
  }

  const studyCap = usage?.caps.find(c => c.feature === "study_regenerate");
  const lifeCap = usage?.caps.find(c => c.feature === "life_adjust");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ borderBottom: "1px solid var(--color-border)", display: "flex" }}>
        <button
          onClick={() => setTab("study")}
          style={{
            flex: 1, padding: "1rem", border: "none", background: "none",
            borderBottom: tab === "study" ? "2px solid var(--color-primary)" : "none",
            fontWeight: tab === "study" ? 600 : 400, color: tab === "study" ? "var(--color-primary)" : "inherit"
          }}
        >
          Study Plan
        </button>
        <button
          onClick={() => setTab("life")}
          style={{
            flex: 1, padding: "1rem", border: "none", background: "none",
            borderBottom: tab === "life" ? "2px solid var(--color-primary)" : "none",
            fontWeight: tab === "life" ? 600 : 400, color: tab === "life" ? "var(--color-primary)" : "inherit"
          }}
        >
          Life Organizer
        </button>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "1.5rem" }}>
        {tab === "study" ? (
          <TierGate requiredTier="premium" upgradePrompt={<UpgradePrompt requiredTier="premium" />}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
                <div>
                  <h2 style={{ fontSize: "var(--font-size-h2)", margin: 0 }}>Litheral Study</h2>
                  <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-caption)" }}>Premium AI assistant for your study schedule.</p>
                </div>
                {studyCap && (
                  <div style={{ textAlign: "right", fontSize: "0.7rem", color: "var(--color-text-secondary)" }}>
                    <div style={{ fontWeight: 600, color: "var(--color-accent-text)" }}>{studyCap.remaining} / {studyCap.limit} left</div>
                    <div>Resets {new Date(studyCap.resets_at).toLocaleDateString()}</div>
                  </div>
                )}
              </div>

              {!studyPlan || studyPlan.length === 0 ? (
                <div style={{ padding: "1.5rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg)" }}>
                  <h3 style={{ fontSize: "var(--font-size-h3)", marginBottom: "1rem" }}>Set your priorities</h3>
                  <StudyPlanConfig subjects={timetableSubjects} onSubmit={handleGenerateStudy} submitting={submitting} />
                </div>
              ) : (
                <div style={{ display: "grid", gap: "1rem" }}>
                  <button type="button" className="btn btn--ghost" onClick={() => setStudyPlan([])} style={{ alignSelf: "flex-end" }}>Re-configure subjects</button>
                  {studyPlan.sort((a,b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(a.start_time)).map(block => (
                    <div key={block.id} style={{ padding: "1rem", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", background: "var(--color-surface)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{block.subject}</div>
                        <div className="tabular-nums" style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)" }}>
                          {DAY_LABELS[block.day_of_week]} · {block.start_time}–{block.end_time}
                        </div>
                      </div>
                      <button type="button" className="btn btn--text" onClick={() => handleRegenerateBlock(block.id)}>Regenerate</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TierGate>
        ) : (
          <TierGate requiredTier="pro" upgradePrompt={<UpgradePrompt requiredTier="pro" />}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
                <div>
                  <h2 style={{ fontSize: "var(--font-size-h2)", margin: 0 }}>Life Organizer</h2>
                  <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-caption)" }}>Pro AI assistant for your whole week.</p>
                </div>
                {lifeCap && (
                  <div style={{ textAlign: "right", fontSize: "0.7rem", color: "var(--color-text-secondary)" }}>
                    <div style={{ fontWeight: 600, color: "var(--color-accent-text)" }}>{lifeCap.remaining} / {lifeCap.limit} left</div>
                    <div>Resets {new Date(lifeCap.resets_at).toLocaleDateString()}</div>
                  </div>
                )}
              </div>

              <div style={{ display: "grid", gap: "2rem" }}>
                <RoutineEditor routines={routines || []} onChanged={fetchData} />

                <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "2rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                    <h3 style={{ fontSize: "var(--font-size-h3)", margin: 0 }}>Weekly Schedule</h3>
                    <button type="button" className="btn btn--primary" onClick={handleGenerateLife} disabled={submitting}>
                      {lifeSchedule && lifeSchedule.length > 0 ? "Re-adjust Schedule" : "Generate Schedule"}
                    </button>
                  </div>

                  {(!lifeSchedule || lifeSchedule.length === 0) ? (
                    <p style={{ color: "var(--color-text-secondary)", textAlign: "center", padding: "2rem" }}>Generate your schedule to see your week organized around your classes and study blocks.</p>
                  ) : (
                    <div style={{ display: "grid", gap: "0.75rem" }}>
                      {lifeSchedule.map(block => (
                        <div
                          key={block.id}
                          style={{
                            padding: "0.75rem",
                            border: "1px solid var(--color-border)",
                            borderRadius: "var(--radius-md)",
                            background: block.conflict_flag ? "rgba(214, 69, 69, 0.05)" : "var(--color-surface)",
                            borderColor: block.conflict_flag ? "var(--color-error)" : "var(--color-border)",
                            display: "flex",
                            justifyContent: "space-between"
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 600 }}>
                              {block.source_type === "routine" ? routines?.find(r => r.id === block.source_id)?.label : block.source_type}
                            </div>
                            <div className="tabular-nums" style={{ fontSize: "var(--font-size-caption)", color: "var(--color-text-secondary)" }}>
                              {DAY_LABELS[block.day_of_week]} · {block.start_time}–{block.end_time}
                            </div>
                          </div>
                          {block.conflict_flag && (
                            <span style={{ color: "var(--color-error)", fontSize: "0.7rem", fontWeight: 700 }}>CONFLICT</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </TierGate>
        )}
      </div>
    </div>
  );
}
