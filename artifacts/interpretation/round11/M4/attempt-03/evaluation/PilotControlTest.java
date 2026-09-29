package assurance;
import org.junit.Test;
import static org.junit.Assert.*;
public class PilotControlTest {
  @Test public void allKnownGiftCases() {
    for(int mask=0; mask<16; mask++) {
      boolean expected = mask==5 || mask==9 || mask==13;
      assertEquals("fixture "+mask,expected,PilotControl.prohibited((mask&1)!=0,(mask&2)!=0,(mask&4)!=0,(mask&8)!=0));
    }
  }
  @Test public void thresholdBoundary() {
    assertFalse(PilotControl.syntheticThreshold(5));
    assertTrue(PilotControl.syntheticThreshold(6));
    assertTrue(PilotControl.syntheticThreshold(7));
  }
}
