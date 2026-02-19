import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CodeAnalysisTab } from "@/components/project/code-analysis-tab";
import { describe, expect, it } from "vitest";

const fullAnalysisPayload = {
  total_files: 42,
  total_lines: 1500,
  code_lines: 1200,
  comment_lines: 300,
  functions: 85,
  classes: 12,
  avg_complexity: 5.2,
  avg_maintainability: 72.5,
  magic_values: 15,
  dead_code: {
    total: 8,
    unused_functions: 3,
    unused_imports: 4,
    unused_variables: 1,
  },
  duplicates: {
    within_file: 5,
    cross_file: 3,
    total_duplicate_lines: 120,
  },
  error_handling_issues: {
    total: 4,
    critical: 1,
    warning: 3,
  },
  naming_issues: 10,
  nesting_issues: 2,
  call_graph_edges: 150,
  data_structures: {
    arrays: 25,
    objects: 40,
  },
  languages: {
    TypeScript: 800,
    Python: 400,
  },
  examples: {
    magic_values: [
      {
        file: "/project/src/utils.ts",
        type: "number",
        value: "42",
        line: 15,
        code_snippet: "const timeout = 42;",
        suggested_name: "DEFAULT_TIMEOUT",
      },
      {
        file: "/project/src/config.ts",
        type: "string",
        value: "localhost",
        line: 8,
        code_snippet: 'const host = "localhost";',
        suggested_name: "DEFAULT_HOST",
      },
    ],
    dead_code: [
      {
        file: "/project/src/helpers.ts",
        type: "function",
        name: "unusedHelper",
        line: 45,
        code_snippet: "function unusedHelper() { }",
        reason: "never called",
        confidence: "high",
      },
    ],
    duplicates: [
      {
        file1: "/project/src/moduleA.ts",
        file2: "/project/src/moduleB.ts",
        line1: 10,
        line2: 25,
        similarity: 0.95,
      },
    ],
    naming_issues: [
      {
        file: "/project/src/index.ts",
        name: "x",
        line: 5,
        issue_type: "too_short",
        suggestion: "Use a more descriptive name",
      },
    ],
    error_handling: [
      {
        file: "/project/src/api.ts",
        line: 30,
        issue_type: "empty_catch",
        severity: "warning",
        code_snippet: "catch(e) { }",
      },
    ],
  },
};

const minimalAnalysisPayload = {
  total_files: 10,
  total_lines: 500,
  code_lines: 400,
  comment_lines: 100,
  functions: 20,
  classes: 3,
};

describe("CodeAnalysisTab", () => {
  describe("Loading and Empty States", () => {
    it("shows loading state when isLoading is true", () => {
      render(<CodeAnalysisTab isLoading={true} />);
      expect(screen.getByText("Analyzing code metrics and quality...")).toBeInTheDocument();
    });

    it("shows error state when errorMessage is provided", () => {
      render(<CodeAnalysisTab errorMessage="Analysis failed" />);
      expect(screen.getByText("Analysis failed")).toBeInTheDocument();
    });

    it("shows empty state when no analysis data exists", () => {
      render(<CodeAnalysisTab />);
      expect(
        screen.getByText("No code analysis data available")
      ).toBeInTheDocument();
    });

    it("shows empty state for empty object", () => {
      render(<CodeAnalysisTab codeAnalysis={{}} />);
      expect(
        screen.getByText("No code analysis data available")
      ).toBeInTheDocument();
    });
  });

  describe("Basic Metrics Display", () => {
    it("renders total files count", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("42")).toBeInTheDocument();
      expect(screen.getByText("Total Files Analyzed")).toBeInTheDocument();
    });

    it("renders total lines count with formatting", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("1,500")).toBeInTheDocument();
      expect(screen.getByText("Total Lines of Code")).toBeInTheDocument();
    });

    it("renders functions count", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("85")).toBeInTheDocument();
      expect(screen.getByText("Functions")).toBeInTheDocument();
    });

    it("renders classes count", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("Classes")).toBeInTheDocument();
    });

    it("renders code composition percentages", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Code Lines")).toBeInTheDocument();
      expect(screen.getByText("Comment Lines")).toBeInTheDocument();
      expect(screen.getByText("1,200")).toBeInTheDocument();
      expect(screen.getByText("300")).toBeInTheDocument();
    });
  });

  describe("Quality Metrics Display", () => {
    it("renders average complexity", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Average Complexity")).toBeInTheDocument();
      expect(screen.getByText("5.20")).toBeInTheDocument();
    });

    it("renders average maintainability", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Average Maintainability")).toBeInTheDocument();
      expect(screen.getByText("72.5")).toBeInTheDocument();
    });

    it("handles missing quality metrics gracefully", () => {
      render(<CodeAnalysisTab codeAnalysis={minimalAnalysisPayload} />);
      expect(screen.queryByText("Average Complexity")).not.toBeInTheDocument();
      expect(screen.queryByText("Average Maintainability")).not.toBeInTheDocument();
    });
  });

  describe("Code Quality Issues Display", () => {
    it("renders dead code detection card", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Dead Code Detection")).toBeInTheDocument();
      expect(screen.getByText(/Unused functions:/)).toBeInTheDocument();
      expect(screen.getByText(/Unused imports:/)).toBeInTheDocument();
      expect(screen.getByText(/Unused variables:/)).toBeInTheDocument();
    });

    it("renders duplicate code detection card", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Duplicate Code Detection")).toBeInTheDocument();
      expect(screen.getByText(/Within-file:/)).toBeInTheDocument();
      expect(screen.getByText(/Cross-file:/)).toBeInTheDocument();
    });

    it("renders magic value detection card", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Magic Value Detection")).toBeInTheDocument();
      expect(screen.getByText("15")).toBeInTheDocument();
    });

    it("renders error handling quality card", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Error Handling Quality")).toBeInTheDocument();
      expect(screen.getByText(/Critical:/)).toBeInTheDocument();
      expect(screen.getByText(/Warnings:/)).toBeInTheDocument();
    });

    it("renders naming convention card", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      expect(screen.getByText("Naming Convention Checking")).toBeInTheDocument();
    });
  });

  describe("Examples Expansion", () => {
    it("shows 'Show examples' button for dead code when examples exist", () => {
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);
      const showButtons = screen.getAllByText(/Show examples/);
      expect(showButtons.length).toBeGreaterThan(0);
    });

    it("expands dead code examples when clicked", async () => {
      const user = userEvent.setup();
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);

      // Find dead code card's show examples button
      const deadCodeCard = screen.getByText("Dead Code Detection").closest("div")!;
      const showButton = deadCodeCard.querySelector("button");
      
      if (showButton) {
        await user.click(showButton);
        expect(screen.getByText("unusedHelper")).toBeInTheDocument();
      }
    });

    it("expands magic values examples when clicked", async () => {
      const user = userEvent.setup();
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);

      // Find magic values card's show examples button
      const magicCard = screen.getByText("Magic Value Detection").closest("div")!;
      const showButton = magicCard.querySelector("button");
      
      if (showButton) {
        await user.click(showButton);
        expect(screen.getByText("DEFAULT_TIMEOUT")).toBeInTheDocument();
      }
    });

    it("expands duplicate examples when clicked", async () => {
      const user = userEvent.setup();
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);

      // Find duplicates card's show examples button
      const dupCard = screen.getByText("Duplicate Code Detection").closest("div")!;
      const showButton = dupCard.querySelector("button");
      
      if (showButton) {
        await user.click(showButton);
        expect(screen.getByText("Similarity: 95%")).toBeInTheDocument();
      }
    });

    it("toggles between Show and Hide examples", async () => {
      const user = userEvent.setup();
      render(<CodeAnalysisTab codeAnalysis={fullAnalysisPayload} />);

      const deadCodeCard = screen.getByText("Dead Code Detection").closest("div")!;
      const showButton = deadCodeCard.querySelector("button");
      
      if (showButton) {
        // Initially shows "Show examples"
        expect(showButton.textContent).toContain("Show");
        
        await user.click(showButton);
        expect(showButton.textContent).toContain("Hide");
        
        await user.click(showButton);
        expect(showButton.textContent).toContain("Show");
      }
    });
  });

  describe("Edge Cases", () => {
    it("handles zero values gracefully", () => {
      const zeroPayload = {
        total_files: 0,
        total_lines: 0,
        code_lines: 0,
        comment_lines: 0,
        functions: 0,
        classes: 0,
        magic_values: 0,
      };
      render(<CodeAnalysisTab codeAnalysis={zeroPayload} />);
      expect(screen.getByText("Total Files Analyzed")).toBeInTheDocument();
    });

    it("handles missing examples gracefully", () => {
      const noExamplesPayload = {
        ...fullAnalysisPayload,
        examples: undefined,
      };
      render(<CodeAnalysisTab codeAnalysis={noExamplesPayload} />);
      expect(screen.getByText("Dead Code Detection")).toBeInTheDocument();
      // Should not show examples button when no examples
      const deadCodeCard = screen.getByText("Dead Code Detection").closest("div")!;
      const showButton = deadCodeCard.querySelector("button");
      expect(showButton).toBeNull();
    });

    it("handles empty examples arrays gracefully", () => {
      const emptyExamplesPayload = {
        ...fullAnalysisPayload,
        examples: {
          magic_values: [],
          dead_code: [],
          duplicates: [],
          naming_issues: [],
          error_handling: [],
        },
      };
      render(<CodeAnalysisTab codeAnalysis={emptyExamplesPayload} />);
      expect(screen.getByText("Dead Code Detection")).toBeInTheDocument();
    });

    it("handles null avg_complexity", () => {
      const nullComplexityPayload = {
        ...minimalAnalysisPayload,
        avg_complexity: null,
      };
      render(<CodeAnalysisTab codeAnalysis={nullComplexityPayload} />);
      expect(screen.queryByText("Average Complexity")).not.toBeInTheDocument();
    });
  });
});
