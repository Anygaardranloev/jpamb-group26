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

    @Case("() -> null pointer")
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
        String s = new String("hey");
        assert s.equals("hey");
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void stringEqualsLiteralFails() {
        String s = new String("hello");
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
        String s = new String("hey");
        assert s == "hey";
    }

    @Case("(0) -> null pointer")
    @Case("(1) -> ok")
    @Tag({ STRING })
    public static void equalsGuardsLengthWrongWay(int i) {
        String s = null;
        if (i == 1) {
            s = "hey";
        }
        if (!"hey".equals(s)) {
            int len = s.length();
        }
    }

    @Case("(0) -> null pointer")
    @Case("(1) -> ok")
    @Tag({ STRING })
    public static void equalsIgnoreCaseGuardsLengthWrongWay(int i) {
        String s = null;
        if (i == 1) {
            s = "HeY";
        }
        if (!"hey".equalsIgnoreCase(s)) {
            int len = s.length();
        }
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
        s = s.substring(1, 3);
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void substringOutOfBounds() {
        String s = "hey";
        s = s.substring(3, 10);
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void substringCharAtInBounds() {
        String s = "hello";
        String t = s.substring(1, 4);
        char c = t.charAt(2);
        assert c == 'l';
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void substringCharAtAssertFails() {
        String s = "hello";
        String t = s.substring(1, 4);
        assert t.charAt(0) == 'x';
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void substringReferenceEquality() {
        String s = "hey";
        String t = s.substring(0, 3);
        assert t.equals("hey");
        assert t == "hey";
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void concatSubstringChainOk() {
        String s = "foobar";
        String left = s.substring(0, 3);
        String right = s.substring(3, 6);
        String result = left.concat(right);
        assert result.equals("foobar");
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void concatSimpleOk() {
        String a = "he";
        String b = "y";
        String c = a.concat(b);
        assert c.equals("hey");
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void concatNested() {
        String s = "he";
        s = s.concat("l").concat("lo");
        assert s.equals("hello");
    }

    @Case("() -> null pointer")
    @Tag({ STRING })
    public static void concatWithNullReceiver() {
        String a = null;
        a = a.concat("x");
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void concatReferenceEquality() {
        String s = "he";
        String t = s.concat("y");
        assert t.equals("hey");
        assert t == "hey";
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void equalsIgnoreCaseOk() {
        String a = "Hey";
        String b = "hEy";
        assert a.equalsIgnoreCase(b);
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void equalsIgnoreCaseFails() {
        String a = "hey";
        String b = "bye";
        assert a.equalsIgnoreCase(b);
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void equalsIgnoreCaseSubstringOk() {
        String s = "HelloWorld";
        String t = s.substring(5, 10);
        assert t.equalsIgnoreCase("world");
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void equalsIgnoreCaseSubstringFails() {
        String s = "HelloWorld";
        String t = s.substring(0, 5);
        assert t.equalsIgnoreCase("world");
    }

    @Case("() -> out of bounds")
    @Tag({ STRING })
    public static void substringIndexArithmeticOutOfBounds() {
        String s = "abcd";
        int i = 1;

        int start = i + 1;
        int end = s.length() + i;

        s = s.substring(start, end);
    }

    @Case("() -> ok")
    @Tag({ STRING })
    public static void substringConcatEqualsIgnoreCaseOk() {
        String s = "  HeLLo  ";
        String core = s.substring(2, 7);
        String result = core.concat("WORLD");
        assert result.equalsIgnoreCase("helloworld");
    }

    @Case("() -> assertion error")
    @Tag({ STRING })
    public static void substringConcatEqualsIgnoreCaseFails() {
        String s = "HELLO!";
        String core = s.substring(0, 5);
        String result = core.concat("X");
        assert result.equalsIgnoreCase("hello");
    }

    @Case("(\"P4ssw0rd\") -> ok")
    @Case("(\"password\") -> assertion error")
    @Tag({ STRING })
    public static void hardPassphrase(String input) {
        String passphrase = "P4ssw0rd";
        assert input.length() == passphrase.length();
        for (int i = 0; i < passphrase.length(); i++) {
            assert input.charAt(i) == passphrase.charAt(i);
        }
    }
}