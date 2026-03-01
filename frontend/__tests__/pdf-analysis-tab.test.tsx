import { render, screen } from "@testing-library/react";
import { PdfAnalysisTab } from "@/components/project/pdf-analysis-tab";
import { describe, expect, it } from "vitest";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const samplePdfAnalysis = [
  {
    file_name: "essay1_dolphin_intelligence.pdf",
    file_path: "essays/essay1_dolphin_intelligence.pdf",
    page_count: 15,
    summary: "This document explores the cognitive abilities of dolphins, including problem-solving, communication, and social learning behaviors.",
    key_topics: ["Cognitive Abilities", "Marine Mammals", "Animal Intelligence"],
    keywords: [
      { word: "dolphins", count: 45 },
      { word: "intelligence", count: 32 },
      { word: "cognitive", count: 28 },
      { word: "communication", count: 24 },
      { word: "behavior", count: 18 },
    ],
    reading_time: 15.5,
    file_size_mb: 2.3,
  },
  {
    file_name: "research_paper.pdf",
    file_path: "docs/research_paper.pdf",
    page_count: 42,
    summary: "A comprehensive research paper on machine learning algorithms and their applications in natural language processing.",
    key_topics: ["Machine Learning", "NLP", "Deep Learning"],
    keywords: [
      { word: "neural", count: 67 },
      { word: "training", count: 54 },
      { word: "model", count: 49 },
      { word: "data", count: 38 },
      { word: "accuracy", count: 31 },
      { word: "algorithm", count: 29 },
      { word: "performance", count: 27 },
      { word: "optimization", count: 24 },
      { word: "classification", count: 22 },
      { word: "evaluation", count: 20 },
      { word: "validation", count: 18 },
      { word: "testing", count: 15 },
    ],
    reading_time: 42.0,
    file_size_mb: 5.8,
  },
  {
    file_name: "quick_guide.pdf",
    file_path: "guides/quick_guide.pdf",
    page_count: 3,
    summary: "A brief introduction to getting started with the software.",
    key_topics: ["Tutorial", "Setup"],
    keywords: [
      { word: "install", count: 8 },
      { word: "configure", count: 5 },
    ],
    reading_time: 3.0,
    file_size_mb: 0.5,
  },
];

const minimalPdfAnalysis = [
  {
    file_name: "minimal.pdf",
    file_path: "minimal.pdf",
    page_count: 1,
  },
];

// ---------------------------------------------------------------------------
// Rendering tests
// ---------------------------------------------------------------------------

describe("PdfAnalysisTab — statistics", () => {
  it("renders all four statistics cards", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    // Check that all stat labels are present
    expect(screen.getByText("Total PDFs")).toBeInTheDocument();
    expect(screen.getByText("Total Pages")).toBeInTheDocument();
    expect(screen.getByText("Avg Pages/PDF")).toBeInTheDocument();
    expect(screen.getByText("Total Minutes")).toBeInTheDocument();

    // Check calculated values
    expect(screen.getByText("3")).toBeInTheDocument(); // 3 PDFs
    expect(screen.getByText("60")).toBeInTheDocument(); // 15 + 42 + 3 = 60 pages
    expect(screen.getByText("20")).toBeInTheDocument(); // 60 / 3 = 20 avg pages
    expect(screen.getByText("61")).toBeInTheDocument(); // 15.5 + 42 + 3 = 60.5 ≈ 61 minutes
  });

  it("shows zeros when no PDFs are present", () => {
    render(<PdfAnalysisTab pdfAnalysis={[]} />);

    const statValues = screen.getAllByText("0");
    expect(statValues.length).toBeGreaterThanOrEqual(4);
  });
});

describe("PdfAnalysisTab — document list", () => {
  it("displays document count in header", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);
    expect(screen.getByText("PDF Documents (3)")).toBeInTheDocument();
  });

  it("renders PDF metadata correctly", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    // File names
    expect(screen.getByText("essay1_dolphin_intelligence.pdf")).toBeInTheDocument();
    expect(screen.getByText("research_paper.pdf")).toBeInTheDocument();
    expect(screen.getByText("quick_guide.pdf")).toBeInTheDocument();

    // File paths
    expect(screen.getByText("essays/essay1_dolphin_intelligence.pdf")).toBeInTheDocument();
    expect(screen.getByText("docs/research_paper.pdf")).toBeInTheDocument();

    // Page counts
    expect(screen.getByText("15 pages")).toBeInTheDocument();
    expect(screen.getByText("42 pages")).toBeInTheDocument();
    expect(screen.getByText("3 pages")).toBeInTheDocument();

    // Reading times
    expect(screen.getByText("16 min")).toBeInTheDocument(); // 15.5 rounded
    expect(screen.getByText("42 min")).toBeInTheDocument();
    expect(screen.getByText("3 min")).toBeInTheDocument();
  });

  it("renders summaries when present", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    expect(
      screen.getByText(/cognitive abilities of dolphins/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/machine learning algorithms/)
    ).toBeInTheDocument();
  });

  it("renders key topics as badges", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    // First document topics
    expect(screen.getByText("Cognitive Abilities")).toBeInTheDocument();
    expect(screen.getByText("Marine Mammals")).toBeInTheDocument();
    expect(screen.getByText("Animal Intelligence")).toBeInTheDocument();

    // Second document topics
    expect(screen.getByText("Machine Learning")).toBeInTheDocument();
    expect(screen.getByText("NLP")).toBeInTheDocument();
    expect(screen.getByText("Deep Learning")).toBeInTheDocument();
  });

  it("renders keywords with counts", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    // First document keywords
    expect(screen.getByText("dolphins")).toBeInTheDocument();
    expect(screen.getByText("(45)")).toBeInTheDocument();
    expect(screen.getByText("intelligence")).toBeInTheDocument();
    expect(screen.getByText("(32)")).toBeInTheDocument();

    // Second document keywords
    expect(screen.getByText("neural")).toBeInTheDocument();
    expect(screen.getByText("(67)")).toBeInTheDocument();
  });

  it("limits keywords to 10 and shows overflow indicator", () => {
    render(<PdfAnalysisTab pdfAnalysis={samplePdfAnalysis} />);

    // Second document has 12 keywords, should show "+2 more"
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("handles minimal PDF data without optional fields", () => {
    render(<PdfAnalysisTab pdfAnalysis={minimalPdfAnalysis} />);

    expect(screen.getByText("minimal.pdf")).toBeInTheDocument();
    expect(screen.getByText("1 pages")).toBeInTheDocument();

    // Should not crash when optional fields are missing
    expect(screen.queryByText("Key Topics:")).not.toBeInTheDocument();
    expect(screen.queryByText("Keywords:")).not.toBeInTheDocument();
  });
});

describe("PdfAnalysisTab — empty states", () => {
  it("shows empty message when no PDFs exist", () => {
    render(<PdfAnalysisTab pdfAnalysis={[]} />);
    expect(
      screen.getByText("No PDF documents found in this project")
    ).toBeInTheDocument();
  });

  it("shows empty message when pdfAnalysis is null", () => {
    render(<PdfAnalysisTab pdfAnalysis={null} />);
    expect(
      screen.getByText("No PDF documents found in this project")
    ).toBeInTheDocument();
  });

  it("shows empty message when pdfAnalysis is undefined", () => {
    render(<PdfAnalysisTab pdfAnalysis={undefined} />);
    expect(
      screen.getByText("No PDF documents found in this project")
    ).toBeInTheDocument();
  });
});

describe("PdfAnalysisTab — loading and error states", () => {
  it("shows loading message while data is being fetched", () => {
    render(<PdfAnalysisTab pdfAnalysis={null} isLoading={true} />);
    expect(screen.getByText("Loading PDF analysis…")).toBeInTheDocument();
  });

  it("shows error message when provided", () => {
    render(
      <PdfAnalysisTab 
        pdfAnalysis={null} 
        isLoading={false} 
        errorMessage="Failed to load PDF analysis" 
      />
    );
    expect(screen.getByText("Failed to load PDF analysis")).toBeInTheDocument();
  });

  it("does not show empty state when loading", () => {
    render(<PdfAnalysisTab pdfAnalysis={null} isLoading={true} />);
    expect(
      screen.queryByText("No PDF documents found in this project")
    ).not.toBeInTheDocument();
  });

  it("does not show empty state when error exists", () => {
    render(
      <PdfAnalysisTab 
        pdfAnalysis={null} 
        errorMessage="Error occurred" 
      />
    );
    expect(
      screen.queryByText("No PDF documents found in this project")
    ).not.toBeInTheDocument();
  });
});

describe("PdfAnalysisTab — data normalization", () => {
  it("handles malformed data gracefully", () => {
    const malformedData: any = [
      null,
      { file_name: "valid.pdf", page_count: 5 },
      "not an object",
      { /* missing file_name */ page_count: 10 },
    ];

    render(<PdfAnalysisTab pdfAnalysis={malformedData} />);

    // Should only render the valid document
    expect(screen.getByText("PDF Documents (1)")).toBeInTheDocument();
    expect(screen.getByText("valid.pdf")).toBeInTheDocument();
  });

  it("provides safe defaults for missing optional fields", () => {
    const minimalData = [
      {
        file_name: "test.pdf",
        page_count: 10,
        // No summary, keywords, topics, etc.
      },
    ];

    render(<PdfAnalysisTab pdfAnalysis={minimalData} />);

    // Should render without crashing
    expect(screen.getByText("test.pdf")).toBeInTheDocument();
    expect(screen.getByText("10 pages")).toBeInTheDocument();
  });

  it("handles empty arrays for keywords and topics", () => {
    const emptyArraysData = [
      {
        file_name: "test.pdf",
        page_count: 5,
        keywords: [],
        key_topics: [],
      },
    ];

    render(<PdfAnalysisTab pdfAnalysis={emptyArraysData} />);

    expect(screen.getByText("test.pdf")).toBeInTheDocument();
    // Should not render the keywords or topics sections
    expect(screen.queryByText("Keywords:")).not.toBeInTheDocument();
    expect(screen.queryByText("Key Topics:")).not.toBeInTheDocument();
  });
});
