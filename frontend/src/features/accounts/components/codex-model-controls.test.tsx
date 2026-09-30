import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/mocks/server";
import { CodexModelControls } from "./codex-model-controls";

const path = "/api/accounts/native/models";

function renderControls(disabled = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CodexModelControls
        accountId="native"
        name="Native account"
        disabled={disabled}
      >
        {({ mode, action }) => (
          <div>
            {mode}
            {action}
          </div>
        )}
      </CodexModelControls>
    </QueryClientProvider>,
  );
}

describe("Codex model controls", () => {
  it("defaults to all models and retains curated choices across mode switches", async () => {
    const user = userEvent.setup();
    renderControls();
    const toggle = await screen.findByRole("switch", { name: /All models/ });
    expect(toggle).toBeChecked();
    await user.click(toggle);
    await user.click(await screen.findByRole("button", { name: "Models (0)" }));
    await user.click(screen.getByRole("checkbox", { name: "gpt-5.4" }));
    await user.click(screen.getByRole("button", { name: "Save 1 model" }));
    await screen.findByRole("button", { name: "Models (1)" });
    await user.click(toggle);
    await screen.findByRole("button", { name: "Models (All)" });
    await user.click(toggle);
    await user.click(await screen.findByRole("button", { name: "Models (1)" }));
    expect(screen.getByRole("checkbox", { name: "gpt-5.4" })).toBeChecked();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("prevents model mutations for read-only accounts", async () => {
    renderControls(true);
    expect(
      await screen.findByRole("switch", { name: /All models/ }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Models (All)" })).toBeDisabled();
  });

  it("reports a failed mode update without changing the saved mode", async () => {
    server.use(
      http.put(path, () =>
        HttpResponse.json(
          { error: { code: "failure", message: "Could not update models" } },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderControls();
    const toggle = await screen.findByRole("switch", { name: /All models/ });
    await user.click(toggle);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not update models",
    );
    expect(toggle).toBeChecked();
  });

  it("preserves unavailable selections and leaves failed saves editable", async () => {
    server.use(
      http.get(path, () =>
        HttpResponse.json({
          allModels: false,
          selectedModels: ["retired"],
          catalog: [],
        }),
      ),
      http.put(path, () =>
        HttpResponse.json(
          { error: { code: "failure", message: "Save failed" } },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderControls();
    await user.click(await screen.findByRole("button", { name: "Models (1)" }));
    const selected = screen.getByRole("checkbox", {
      name: /retired.*Unavailable/,
    });
    expect(selected).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Save 1 model" }));
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toHaveTextContent("Save failed"),
    );
    expect(selected).toBeChecked();
    expect(screen.getByRole("button", { name: "Save 1 model" })).toBeEnabled();
  });

  it("allows retrying a failed settings load", async () => {
    let calls = 0;
    server.use(
      http.get(path, () =>
        ++calls === 1
          ? HttpResponse.json(
              { error: { code: "failure", message: "Unavailable" } },
              { status: 500 },
            )
          : HttpResponse.json({
              allModels: true,
              selectedModels: [],
              catalog: [],
            }),
      ),
    );
    const user = userEvent.setup();
    renderControls();
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("switch", { name: /All models/ }),
    ).toBeChecked();
  });
});
