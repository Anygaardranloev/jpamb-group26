#Bytecode instructions
| Mnemonic | Opcode Name |  Exists in |  Count |
| :---- | :---- | :----- | -----: |
 | [iconst_i](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iconst_i) | [Push](jpamb/jvm/opcode.py?plain=1#L116) |  Arrays Loops Simple Tricky | 120 |
 | [iload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L653) |  Arrays Loops Simple Tricky | 92 |
 | [if_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_cond) | [Ifz](jpamb/jvm/opcode.py?plain=1#L818) |  Arrays Loops Simple Strings Tricky | 70 |
 | [dup](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.dup) | [Dup](jpamb/jvm/opcode.py?plain=1#L221) |  Arrays Loops Simple Strings Tricky | 61 |
 | [return](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.return) | [Return](jpamb/jvm/opcode.py?plain=1#L1044) |  Arrays Calls Loops Strings Tricky | 47 |
 | [aload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L653) |  Arrays Strings | 45 |
 | [ldc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ldc) | [Push](jpamb/jvm/opcode.py?plain=1#L116) |  Arrays Strings | 40 |
 | [if_icmp_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_icmp_cond) | [If](jpamb/jvm/opcode.py?plain=1#L692) |  Arrays Tricky | 38 |
 | [getstatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.getstatic) | [Get](jpamb/jvm/opcode.py?plain=1#L757) |  Arrays Loops Simple Strings Tricky | 38 |
 | [new](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.new) | [New](jpamb/jvm/opcode.py?plain=1#L886) |  Arrays Loops Simple Strings Tricky | 38 |
 | [invokespecial](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokespecial) | [InvokeSpecial](jpamb/jvm/opcode.py?plain=1#L498) |  Arrays Loops Simple Strings Tricky | 38 |
 | [athrow](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.athrow) | [Throw](jpamb/jvm/opcode.py?plain=1#L925) |  Arrays Loops Simple Strings Tricky | 38 |
 | [istore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L548) |  Arrays Loops Tricky | 29 |
 | [iastore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iastore) | [ArrayStore](jpamb/jvm/opcode.py?plain=1#L256) |  Arrays | 28 |
 | [idiv](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.idiv) | [Binary](jpamb/jvm/opcode.py?plain=1#L616) |  Arrays Simple Tricky | 20 |
 | [ireturn](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ireturn) | [Return](jpamb/jvm/opcode.py?plain=1#L1044) |  Simple | 20 |
 | [goto](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.goto) | [Goto](jpamb/jvm/opcode.py?plain=1#L1004) |  Arrays Loops Tricky | 18 |
 | [astore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.astore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L548) |  Arrays Strings | 17 |
 | [caload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.caload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L322) |  | 15 |
 | [arraylength](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.arraylength) | [ArrayLength](jpamb/jvm/opcode.py?plain=1#L356) |  Arrays | 12 |
 | [iload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload) | [Load](jpamb/jvm/opcode.py?plain=1#L653) |  Arrays | 11 |
 | [iadd](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iadd) | [Binary](jpamb/jvm/opcode.py?plain=1#L616) |  Arrays Loops Tricky | 10 |
 | [invokestatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokestatic) | [InvokeStatic](jpamb/jvm/opcode.py?plain=1#L425) |  Calls | 10 |
 | [iaload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iaload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L322) |  Arrays | 9 |
 | [newarray](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.newarray) | [NewArray](jpamb/jvm/opcode.py?plain=1#L182) |  Arrays | 8 |
 | [isub](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.isub) | [Binary](jpamb/jvm/opcode.py?plain=1#L616) |  Arrays | 8 |
 | [iinc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iinc) | [Incr](jpamb/jvm/opcode.py?plain=1#L962) |  | 6 |
 | [istore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore) | [Store](jpamb/jvm/opcode.py?plain=1#L548) |  Arrays | 5 |
 | [aconst_null](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aconst_null) | [Push](jpamb/jvm/opcode.py?plain=1#L116) |  | 4 |
 | [imul](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.imul) | [Binary](jpamb/jvm/opcode.py?plain=1#L616) |  Tricky | 3 |
 | [invokevirtual](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokevirtual) | [InvokeVirtual](jpamb/jvm/opcode.py?plain=1#L390) |  Strings | 2 |
 | [irem](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.irem) | [Binary](jpamb/jvm/opcode.py?plain=1#L616) |  Tricky | 2 |
 | [i2s](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.i2s) | [Cast](jpamb/jvm/opcode.py?plain=1#L288) |  Loops | 1 |
