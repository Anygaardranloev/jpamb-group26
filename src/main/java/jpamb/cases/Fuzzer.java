package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Fuzzer {

    @Case("(\"P4ssw0rd\") -> assertion error")
    @Case("(\"password\") -> ok")
    @Tag({ FUZZER })
    public static void assertOnlyCorrectPasswordNestedBranches(String password) {
        String correct = "P4ssw0rd";

        if (password.length() == correct.length()) {
            if (correct.charAt(0) == password.charAt(0)) {
                if (correct.charAt(1) == password.charAt(1)) {
                    if (correct.charAt(2) == password.charAt(2)) {
                        if (correct.charAt(3) == password.charAt(3)) {
                            if (correct.charAt(4) == password.charAt(4)) {
                                if (correct.charAt(5) == password.charAt(5)) {
                                    if (correct.charAt(6) == password.charAt(6)) {
                                        if (correct.charAt(7) == password.charAt(7)) {
                                            assert false;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    @Case("(\"P4ssw0rd\") -> assertion error")
    @Case("(\"P4ssTEST\") -> assertion error")
    @Case("(\"password\") -> ok")
    @Tag({ FUZZER })
    public static void assertMultiplePossibleCrashInputsNestedBranches(String password) {
        String correct1 = "P4ssw0rd";
        String correct2 = "P4ssTEST";

        if (password.length() == correct1.length()) {
            if (correct1.charAt(0) == password.charAt(0)) {
                if (correct1.charAt(1) == password.charAt(1)) {
                    if (correct1.charAt(2) == password.charAt(2)) {
                        if (correct1.charAt(3) == password.charAt(3)) {
                            if (correct1.charAt(4) == password.charAt(4)) {
                                if (correct1.charAt(5) == password.charAt(5)) {
                                    if (correct1.charAt(6) == password.charAt(6)) {
                                        if (correct1.charAt(7) == password.charAt(7)) {
                                            assert false;
                                        }
                                    }
                                }
                            }

                            if (correct2.charAt(4) == password.charAt(4)) {
                                if (correct2.charAt(5) == password.charAt(5)) {
                                    if (correct2.charAt(6) == password.charAt(6)) {
                                        if (correct2.charAt(7) == password.charAt(7)) {
                                            assert false;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    @Case("(\"C0d3W0rD\") -> assertion error")
    @Case("(\"11111111\") -> ok")
    @Tag({ FUZZER })
    public static void assertOnlyCorrectPasswordLoop(String password) {
        String correct = "C0d3W0rD";

        if (password.length() != correct.length()) {
            return;
        }

        for (int i = 0; i < correct.length(); i++) {
            if (correct.charAt(i) != password.charAt(i)) {
                return;
            }
        }

        assert false;
    }

    @Tag({ FUZZER })
    public static void assertOnlyCorrectPasswordSubstring(String password) {
        String correct = "S3cur3P@ss";
        if (password.length() < 20) {
            return;
        }

        String sub = password.substring(7, 7 + correct.length());
        if (sub.equals(correct)) {
            assert false;
        }
    }

    @Case("(322428591) -> assertion error")
    @Case("(11111111) -> ok")
    @Tag({ FUZZER })
    public static void assertOnlyCorrectU32IntegerMagic(int number) {
        if (number == 0x1337DEAF) {
            assert false;
        }
    }

    @Case("(\"X-API-KEY: secret-key-s3cur3p4ss\", 305419896) -> assertion error")
    @Case("(\"X-API-KEY: wrong\", 0) -> ok")
    @Case("(\"X-OTHER: secret-key-123\", 0) -> ok")
    @Tag({ FUZZER })
    public static void assertOnlyCorrectHeaderFormat(String header, int magic) {
        String requiredPrefix = "X-API-KEY: ";
        String secret = "secret-key-s3cur3p4ss";

        if (header.length() < requiredPrefix.length() + secret.length()) {
            return;
        }

        String prefix = header.substring(0, requiredPrefix.length());
        if (!prefix.equals(requiredPrefix)) {
            return;
        }

        String candidate = header.substring(requiredPrefix.length(), requiredPrefix.length() + secret.length());
        if (candidate.equals(secret) && magic == 0x12345678) {
            assert false;
        }
    }
}