import { Check, X, Minus } from "lucide-react";

type ComparisonValue = boolean | string;

interface ComparisonRow {
  feature: string;
  tradeflow: ComparisonValue;
  alternative: ComparisonValue;
}

const comparisons: ComparisonRow[] = [
  { feature: "Setup Time", tradeflow: "2 minutes", alternative: "Hours/Days" },
  { feature: "Multi-Broker Support", tradeflow: true, alternative: false },
  { feature: "TradingView Native", tradeflow: true, alternative: "varies" },
  { feature: "Secure Credentials", tradeflow: true, alternative: "varies" },
  { feature: "Position Sizing", tradeflow: true, alternative: false },
  { feature: "Maintenance Required", tradeflow: "None", alternative: "Ongoing" },
  { feature: "Starting Price", tradeflow: "Free", alternative: "$20+/mo" },
];

function ComparisonCell({ value }: { value: ComparisonValue }) {
  if (value === true) {
    return <Check className="h-5 w-5 text-green-500 mx-auto" />;
  }
  if (value === false) {
    return <X className="h-5 w-5 text-red-500 mx-auto" />;
  }
  if (value === "varies") {
    return <Minus className="h-5 w-5 text-yellow-500 mx-auto" />;
  }
  return <span className="font-medium">{value}</span>;
}

export function Comparison() {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Why Tradeflow?
        </h2>
        <p className="text-center text-muted-foreground mb-12 text-lg">
          See how Tradeflow compares to the alternatives
        </p>

        <div className="max-w-3xl mx-auto overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                <th className="text-left py-4 px-4 font-semibold text-muted-foreground">
                  Feature
                </th>
                <th className="text-center py-4 px-4 bg-primary/10 rounded-t-lg font-semibold">
                  Tradeflow
                </th>
                <th className="text-center py-4 px-4 font-semibold text-muted-foreground">
                  Alternatives
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((row, index) => (
                <tr
                  key={row.feature}
                  className={index < comparisons.length - 1 ? "border-b" : ""}
                >
                  <td className="py-4 px-4 text-sm">{row.feature}</td>
                  <td className="py-4 px-4 text-center text-sm bg-primary/5">
                    <ComparisonCell value={row.tradeflow} />
                  </td>
                  <td className="py-4 px-4 text-center text-sm text-muted-foreground">
                    <ComparisonCell value={row.alternative} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-center text-muted-foreground mt-8 text-sm">
          Stop wasting time with manual trading or unreliable scripts.
        </p>
      </div>
    </section>
  );
}
