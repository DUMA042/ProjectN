import { Component, ReactNode } from "react";

interface State {
  error: Error | null;
}

interface Props {
  children: ReactNode;
  label?: string;
}

/** Catches render crashes inside a subtree and shows a recoverable error card
 * instead of blanking the whole app. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    console.error("UI crash caught by boundary:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card-container p-8 text-center">
          <p className="text-sm font-semibold text-danger">
            Something broke while rendering {this.props.label || "this view"}.
          </p>
          <p className="text-xs text-text-secondary mt-1.5 max-w-md mx-auto break-words">
            {this.state.error.message}
          </p>
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => this.setState({ error: null })}
              className="px-4 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity"
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover transition-colors"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
