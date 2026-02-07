import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentAnalysisTab } from "@/components/project/document-analysis-tab";
import { describe, expect, it } from "vitest";

const analysisPayload = {
  documents: [
    {
      file_name: "docs/Spec.md",
      summary: "API specification and integration details.",
      metadata: {
        word_count: 1200,
        headings: ["Overview", "Endpoints"],
      },
      keywords: [{ word: "api" }, ["design", 3]],
      success: true,
    },
    {
      file_name: "notes/release.txt",
      summary: "Release notes for sprint 4.",
      metadata: {
        word_count: 200,
      },
      keywords: ["release"],
      headings: [],
      success: true,
    },
    {
      file_name: "bad.docx",
      success: false,
    },
  ],
};

describe("DocumentAnalysisTab", () => {
  it("renders backend document analysis payload", () => {
    render(<DocumentAnalysisTab documentAnalysis={analysisPayload} />);

    expect(screen.getByText("Spec.md")).toBeInTheDocument();
    expect(screen.getByText("API specification and integration details.")).toBeInTheDocument();
    expect(screen.getByText("1,200 words")).toBeInTheDocument();
    expect(screen.getByText("api")).toBeInTheDocument();
    expect(screen.getByText("design")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.queryByText("bad.docx")).not.toBeInTheDocument();
  });

  it("shows empty state when no analysis exists", () => {
    render(<DocumentAnalysisTab />);
    expect(
      screen.getByText("No document analysis available for this project yet")
    ).toBeInTheDocument();
  });

  it("filters documents by search and file type", async () => {
    const user = userEvent.setup();
    render(<DocumentAnalysisTab documentAnalysis={analysisPayload} />);

    await user.type(
      screen.getByPlaceholderText("Search documents by name, title, or topic..."),
      "release"
    );

    expect(screen.getByText("release.txt")).toBeInTheDocument();
    expect(screen.queryByText("Spec.md")).not.toBeInTheDocument();

    await user.clear(
      screen.getByPlaceholderText("Search documents by name, title, or topic...")
    );

    await user.selectOptions(screen.getByRole("combobox"), "md");
    expect(screen.getByText("Spec.md")).toBeInTheDocument();
    expect(screen.queryByText("release.txt")).not.toBeInTheDocument();
  });
});
