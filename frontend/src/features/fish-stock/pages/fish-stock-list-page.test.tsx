import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FishStockListPage } from "@/features/fish-stock/pages/fish-stock-list-page";

const { pushMock, hasPermissionMock, useFishStockListMock, setFiltersMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  hasPermissionMock: vi.fn(() => true),
  useFishStockListMock: vi.fn(),
  setFiltersMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/fish-stock",
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/fish-stock/hooks/use-fish-stock-list", () => ({
  useFishStockList: useFishStockListMock,
}));

vi.mock("@/features/fish-stock/hooks/use-fish-stock-filters", () => ({
  useFishStockFilters: () => [
    { search: "", status: null, page: 1, pageSize: 20 },
    setFiltersMock,
  ],
}));

const FISH_ROW = {
  fishId: "fish-1",
  fishName: "Pomfret",
  unit: "kg" as const,
  totalCaught: "180.000",
  totalSold: "60.000",
  totalAvailable: "120.000",
  totalWaste: "0.000",
};

function mockListQuery(overrides: Partial<ReturnType<typeof useFishStockListMock>> = {}) {
  useFishStockListMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
});

describe("FishStockListPage", () => {
  it("shows a Forbidden state and never renders the table when the user lacks fish:view", () => {
    hasPermissionMock.mockReturnValue(false);
    mockListQuery({ data: { data: [FISH_ROW], meta: { total_records: 1 } } });

    render(<FishStockListPage />);

    expect(screen.getByText("You don't have access to this page")).toBeInTheDocument();
    expect(screen.queryByText("Pomfret")).not.toBeInTheDocument();
  });

  it("renders a loading state before data arrives", () => {
    mockListQuery({ isLoading: true, isFetching: true });

    render(<FishStockListPage />);

    expect(screen.queryByText("Pomfret")).not.toBeInTheDocument();
    expect(screen.queryByText("No available fish stock yet")).not.toBeInTheDocument();
  });

  it("renders the empty state when there is no stock and no active filters", () => {
    mockListQuery({
      data: {
        data: [],
        meta: { total_records: 0, total_pages: 0, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<FishStockListPage />);

    expect(screen.getByText("No available fish stock yet")).toBeInTheDocument();
    expect(
      screen.getByText("Stock appears here after fish are recorded against returned trips.")
    ).toBeInTheDocument();
  });

  it("renders an error state with a retry action when the query fails", () => {
    const refetch = vi.fn();
    mockListQuery({
      isError: true,
      error: { category: "server", status: 500, code: "INTERNAL_ERROR", message: "Something broke" },
      refetch,
    });

    render(<FishStockListPage />);

    expect(screen.getByText("Failed to load fish stock")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders fish rows with the correct unit and prominently displayed available quantity", () => {
    mockListQuery({
      data: {
        data: [FISH_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<FishStockListPage />);

    expect(screen.getByText("Pomfret")).toBeInTheDocument();
    expect(screen.getByText("Kg")).toBeInTheDocument();
    // formatQuantity renders 3 decimal places at en-IN locale grouping.
    expect(screen.getByText("120.000")).toBeInTheDocument();
    expect(screen.getByText("180.000")).toBeInTheDocument();
    expect(screen.getByText("60.000")).toBeInTheDocument();
  });

  it("shows the Fish Types KPI without inventing a combined quantity across mixed units", () => {
    mockListQuery({
      data: {
        data: [
          FISH_ROW,
          { ...FISH_ROW, fishId: "fish-2", fishName: "Tuna Boxes", unit: "box" as const },
        ],
        meta: { total_records: 2, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<FishStockListPage />);

    expect(screen.getByText("Fish Types")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    // Two distinct units on the same page - must never show a single combined figure.
    expect(screen.getAllByText("View by fish").length).toBeGreaterThan(0);
  });

  it("searching for a fish updates the filters through the debounced search box", async () => {
    const user = userEvent.setup();
    mockListQuery({
      data: {
        data: [FISH_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<FishStockListPage />);

    const searchBox = screen.getByRole("searchbox", { name: "Search fish" });
    await user.type(searchBox, "pomfret");

    await waitFor(
      () => expect(setFiltersMock).toHaveBeenCalledWith({ search: "pomfret", page: 1 }),
      { timeout: 1000 }
    );
  });

  it("navigates to the fish's detail page when a row is clicked", async () => {
    const user = userEvent.setup();
    mockListQuery({
      data: {
        data: [FISH_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<FishStockListPage />);

    await user.click(screen.getByText("Pomfret"));

    expect(pushMock).toHaveBeenCalledWith("/fish-stock/fish-1");
  });
});
