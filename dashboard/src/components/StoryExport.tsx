import { useGameStore } from "../store/gameStore";

const SCENARIO_NAMES: Record<string, string> = {
  last_train: "The Last Train",
  locked_room: "The Locked Room",
  dinner_party: "The Dinner Party",
  the_signal: "The Signal",
};

export async function exportStoryPDF() {
  const { loopHistory, clues, scenario, currentLoop } =
    useGameStore.getState();

  if (loopHistory.length === 0) {
    alert("No story to export yet!");
    return;
  }

  const [{ default: jsPDF }] = await Promise.all([
    import("jspdf"),
    import("html2canvas"),
  ]);

  const pdf = new jsPDF("p", "mm", "a4");
  const pageWidth = pdf.internal.pageSize.getWidth();
  const margin = 15;
  const contentWidth = pageWidth - margin * 2;

  // Title page
  pdf.setFontSize(36);
  pdf.setTextColor(124, 111, 245);
  pdf.text("ECHOES", pageWidth / 2, 55, { align: "center" });

  pdf.setFontSize(18);
  pdf.setTextColor(100, 100, 140);
  const scenarioName = scenario
    ? SCENARIO_NAMES[scenario] ?? scenario
    : "Mystery";
  pdf.text(scenarioName, pageWidth / 2, 70, { align: "center" });

  pdf.setFontSize(10);
  pdf.setTextColor(140, 140, 160);
  pdf.text(
    `${currentLoop} loops | ${clues.length} clues discovered`,
    pageWidth / 2,
    82,
    { align: "center" },
  );
  pdf.text(
    `Generated on ${new Date().toLocaleDateString()}`,
    pageWidth / 2,
    90,
    { align: "center" },
  );

  // Loop pages
  pdf.addPage();
  let yPos = 20;

  pdf.setFontSize(20);
  pdf.setTextColor(60, 60, 80);
  pdf.text("Loop History", margin, yPos);
  yPos += 12;

  for (const entry of loopHistory) {
    if (yPos > 250) {
      pdf.addPage();
      yPos = 20;
    }

    // Loop header
    pdf.setFontSize(14);
    pdf.setTextColor(124, 111, 245);
    const statusIcon = entry.status === "broken" ? "[BROKEN]" : "[FAILED]";
    pdf.text(`Loop ${entry.loop_number} ${statusIcon}`, margin, yPos);
    yPos += 7;

    // Duration
    pdf.setFontSize(9);
    pdf.setTextColor(140, 140, 160);
    const mins = Math.floor(entry.duration_seconds / 60);
    const secs = entry.duration_seconds % 60;
    pdf.text(`Duration: ${mins}m ${secs}s`, margin, yPos);
    yPos += 6;

    // Summary
    pdf.setFontSize(11);
    pdf.setTextColor(60, 60, 80);
    const summaryLines = pdf.splitTextToSize(entry.summary, contentWidth);
    if (yPos + summaryLines.length * 5 > 270) {
      pdf.addPage();
      yPos = 20;
    }
    pdf.text(summaryLines, margin, yPos);
    yPos += summaryLines.length * 5 + 3;

    // Death description
    if (entry.death_description && entry.status === "failed") {
      pdf.setFontSize(10);
      pdf.setTextColor(255, 71, 87);
      const deathLines = pdf.splitTextToSize(
        entry.death_description,
        contentWidth,
      );
      pdf.text(deathLines, margin, yPos);
      yPos += deathLines.length * 5 + 3;
    }

    // Clues found
    if (entry.clues_found.length > 0) {
      pdf.setFontSize(9);
      pdf.setTextColor(245, 166, 35);
      pdf.text(
        `Clues discovered: ${entry.clues_found.join(", ")}`,
        margin,
        yPos,
      );
      yPos += 6;
    }

    yPos += 6;
  }

  // Clues page
  if (clues.length > 0) {
    pdf.addPage();
    yPos = 20;

    pdf.setFontSize(20);
    pdf.setTextColor(245, 166, 35);
    pdf.text("Clues Collected", margin, yPos);
    yPos += 12;

    for (const clue of clues) {
      if (yPos > 260) {
        pdf.addPage();
        yPos = 20;
      }

      pdf.setFontSize(11);
      pdf.setTextColor(60, 60, 80);
      const prefix = clue.is_key_clue ? "[KEY] " : "";
      const clueLines = pdf.splitTextToSize(
        `${prefix}${clue.text}`,
        contentWidth,
      );
      pdf.text(clueLines, margin, yPos);
      yPos += clueLines.length * 5 + 2;

      pdf.setFontSize(9);
      pdf.setTextColor(140, 140, 160);
      pdf.text(`Discovered in Loop ${clue.loop_discovered}`, margin, yPos);
      yPos += 5;

      if (clue.detail) {
        const detailLines = pdf.splitTextToSize(clue.detail, contentWidth);
        pdf.text(detailLines, margin, yPos);
        yPos += detailLines.length * 4 + 4;
      }

      yPos += 4;
    }
  }

  pdf.save(`echoes-${scenario ?? "mystery"}-${Date.now()}.pdf`);
}
