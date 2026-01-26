# Weight Analysis Script

modes = {
    "Safest": {"risk_weight": 0.8, "distance_weight": 0.2},
    "Balanced": {"risk_weight": 0.6, "distance_weight": 0.4},
    "Fastest": {"risk_weight": 0.3, "distance_weight": 0.7}
}

risks = [0.1, 0.3, 0.5, 0.7, 0.9]
length = 1000  # meters

print("Cost Analysis for 1000m Road Segment:\n")
print(f"{'Mode':<12} {'Risk=0.1':<12} {'Risk=0.3':<12} {'Risk=0.5':<12} {'Risk=0.7':<12} {'Risk=0.9':<12}")
print("-" * 75)

for mode_name, weights in modes.items():
    rw = weights["risk_weight"]
    dw = weights["distance_weight"]
    costs = []
    for risk in risks:
        cost = (length * dw) + (length * risk * rw)
        costs.append(f"{cost:.0f}")
    print(f"{mode_name:<12} {costs[0]:<12} {costs[1]:<12} {costs[2]:<12} {costs[3]:<12} {costs[4]:<12}")

print("\nCost Difference (Risky vs Safe Road):")
print("=" * 75)
for mode_name, weights in modes.items():
    rw = weights["risk_weight"]
    dw = weights["distance_weight"]
    safe_cost = (length * dw) + (length * 0.1 * rw)
    risky_cost = (length * dw) + (length * 0.9 * rw)
    diff = risky_cost - safe_cost
    print(f"{mode_name:<12}: Safe={safe_cost:.0f}, Risky={risky_cost:.0f}, Diff={diff:.0f} ({diff/safe_cost*100:.1f}% penalty)")
