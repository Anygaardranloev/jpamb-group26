package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Strings {

    // null safety
    @Case("(\"hello\") -> ok")
    @Case("(null) -> null pointer")
    @Tag({ STRING })
    public static void stringIsNull(String s) {
        assert s != null;
    }

    // length safety
    @Case("(\"hello\") -> ok")
    @Case("(\"\") -> assertion error")
    @Tag({ STRING })
    public static void stringEmpty(String s) {
        assert s.length() > 0;
    }

    @Case("(\"hello\") -> ok")
    @Case("(\"hey\") -> assertion error")
    @Tag({ STRING })
    public static void stringLengthAssertion(String s) {
        assert s.length() == 5;
    }


    // equality
    @Case("(\"hello\") -> ok")
    @Tag({ STRING })
    public static void stringReferenceEqualityOk(String s) {
        String t = "hello";
        assert s == t;
    }

    @Case("(\"hello\") -> assertion error")
    @Tag({ STRING })
    public static void stringReferenceEqualityFail(String s) {
        String t = new String ("hello");
        assert s == t;
    }


    // index and bounds
    @Case("(\"hello\") -> ok")
    @Case("(\"hey\") -> out of bounds")
    @Tag({ STRING })
    public static void charAtBounds(String s) {
        char c = s.charAt(4);
    }

    @Case("(\"hello\") -> ok")
    @Case("(\"hey\") -> out of bounds")
    @Tag({ STRING })
    public static void substringBounds(String s) {
        String t = s.substring(1,4);
    }


    // assertions
    @Case("(\"hello\") -> ok")
    @Case("(\"hey\") -> assertion error")
    @Tag({ STRING })
    public static void assertLiteralEqual(String s) {
        String t = "hello";
        assert s.equals(t);
    }

    @Case("(\"hello\") -> ok")
    @Case("(\"hey\") -> assertion error")
    @Tag({ STRING })
    public static void stringSpellsHello(String s) {
        assert s.charAt(0) == 'h'
            && s.charAt(1) == 'e'
            && s.charAt(2) == 'l'
            && s.charAt(3) == 'l'
            && s.charAt(4) == 'o';
    }

    @Case("(\"hi\") -> out of bounds")
    @Case("(\"hello\") -> assertion error")
    @Case("(\"\") -> assertion error")
    @Tag({ STRING })
    public static void stringSpellsHey(String s) {
        assert s.charAt(0) == 'h'
            && s.charAt(1) == 'e'
            && s.charAt(2) == 'y';
    }
}