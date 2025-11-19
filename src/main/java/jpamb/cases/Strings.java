package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Strings {

    @Case("(\"hey\") -> ok")
    @Case("(\"hey\") -> assertion error")
    @Tag({ STRING })
    public static void assertEqual(String s) {
        String t = "hello";
        assert s.equals(t);
    }

}