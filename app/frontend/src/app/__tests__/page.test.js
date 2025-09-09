import { Navbar } from "@/components";
import { render } from "@testing-library/react";

describe("HomePage", () => {
  it("renders login button when session empty", () => {
    const { getByText } = render(<Navbar />);
    expect(getByText("LOGIN")).toBeInTheDocument();
  });

  it("renders profile button when session exists", () => {
    const { getByLabelText } = render(<Navbar session={{ id: 1 }} />);

    expect(getByLabelText("Profile")).toBeInTheDocument();
  });

  it("renders correctly & match with the snapshot", () => {
    const { container } = render(<Navbar session={{ id: 1 }} />);
    expect(container).toMatchSnapshot();
  });
});
