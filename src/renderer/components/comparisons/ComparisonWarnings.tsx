type ComparisonWarningsProps = {
  warnings: string[];
  error: string | null;
};

export function ComparisonWarnings({ warnings, error }: ComparisonWarningsProps) {
  return (
    <>
      {error && <div className="comparison-message comparison-error" role="alert">{error}</div>}
      {warnings.length > 0 && (
        <div className="comparison-message comparison-warning" role="status">
          {warnings.map((warning) => <p key={warning}>{warning}</p>)}
        </div>
      )}
    </>
  );
}
