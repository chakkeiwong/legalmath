import java.nio.file.Files;
import java.nio.file.Path;
public final class LegalMathHost {
  private LegalMathHost() {}
  public static void main(String[] args) throws Exception {
    if(args.length!=3) throw new IllegalArgumentException("snapshot, rule, UTC assessment time required");
    String snapshot=Files.readString(Path.of(args[0]));
    System.out.println(hk.legalmath.Policy_d5f9b68bbb328a7bafe7.evaluate(snapshot,args[1],args[2],args[2],"draft"));
  }
}
