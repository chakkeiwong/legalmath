package assurance;
public final class PilotControl {
  private PilotControl() {}
  public static boolean prohibited(boolean gift, boolean discount, boolean specific, boolean typeLink) {
    return gift && !discount && (specific || typeLink);
  }
  public static boolean syntheticThreshold(int months) { return months >= 6; }
}
