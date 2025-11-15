package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Strings {

    // null safety
    @Case("(null) -> null pointer")
    @Tag({ STRING })
    public static void lenOfNull() {
        String s = null;
        s.length();
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void lenOfNonNull() {
        String s = "null";
        int x = s.length();
    }

    @Case("(11) -> null pointer")
    @Case("(0) -> ok")
    @Tag({ STRING })
    public static void stringLenSometimesNull(int i) {
        String s = null;
        if (i < 10) {
            s = "x";
        }
        s.length();
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void charAtNull() {
        String s = null;
        s.charAt(0);
    }

    // length safety
    @Case("() -> ok")
    @Tag({ STRING })
    public static void stringLengthAssertionOk() {
        String s = "hey";
        assert s.length() == 3;
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringLengthAssertionFails() {
        String s = "hey";
        assert s.length() == 10;
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void stringIsEmptyOk() {
        String s = "";
        assert s.length() == 0;
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringIsEmptyFails() {
        String s = "hey";
        assert s.length() == 0;
    }

    // assertions
    @Case("() -> ok")
    @Tag({ STRING })
    public static void stringSpellsHeyOk() {
        String s = "hey";
        assert s.charAt(0) == 'h'
            && s.charAt(1) == 'e'
            && s.charAt(2) == 'y';
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void stringSpellsHeyFails() {
        String s = "hello";
        assert s.charAt(0) == 'h'
            && s.charAt(1) == 'e'
            && s.charAt(2) == 'y';
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringSpellsHeyEmpty() {
        String s = "";
        assert s.charAt(0) == 'h'
            && s.charAt(1) == 'e'
            && s.charAt(2) == 'y';
    }

    // equality
    @Case("() -> ok")
    @Tag({ STRING })
    public static void stringEqualsLiteralOk() {
        String s = new String ("hey");
        assert s.equals("hey");
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringEqualsLiteralFails() {
        String s = new String ("hello");
        assert s.equals("hey");
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void stringReferenceEqualityOk() {
        String s = "hey";
        assert s == "hey";
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringReferenceEqualityFails() {
        String s = new String ("hey");
        assert s == "hey";
    }

    // index and bounds
    @Case("() -> ok")
    @Tag({ STRING })
    public static void charAtInBounds() {
        String s = "hey";
        char c = s.charAt(1);
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void charAtOutOfBounds() {
        String s = "hey";
        char c = s.charAt(10);
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void substringInBounds() {
        String s = "hello";
        s.substring = s.substring(1,3);
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void substringOutOfBounds() {
        String s = "hey";
        s.substring = s.substring(3,10);
    }

}