package hk.legalmath;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Strict canonical_v1 JSON, with no external runtime dependency. */
public final class Json {
    private Json() {}
    public static final class Invalid extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;
        public Invalid() { super("Invalid canonical_v1 JSON"); }
    }
    public static Object parse(String text) {
        if (text.getBytes(StandardCharsets.UTF_8).length > 20 * 1024 * 1024) throw new Invalid();
        Parser p = new Parser(text);
        Object value = p.value(0);
        p.space();
        if (p.i != text.length()) throw new Invalid();
        write(value);
        return value;
    }
    @SuppressWarnings("unchecked")
    public static Map<String,Object> map(Object value) {
        if (!(value instanceof Map<?,?>)) throw new Invalid();
        return (Map<String,Object>)value;
    }
    @SuppressWarnings("unchecked")
    public static List<Object> list(Object value) {
        if (!(value instanceof List<?>)) throw new Invalid();
        return (List<Object>)value;
    }
    public static String str(Object value) {
        if (!(value instanceof String)) throw new Invalid();
        return (String)value;
    }
    public static Map<String,Object> obj(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0; i<values.length; i+=2) result.put((String)values[i], values[i+1]);
        return result;
    }
    public static Object freeze(Object value) {
        if (value instanceof Map<?,?>) {
            Map<String,Object> out = new LinkedHashMap<>();
            map(value).forEach((k,v)->out.put(k,freeze(v)));
            return Collections.unmodifiableMap(out);
        }
        if (value instanceof List<?>) {
            List<Object> out = new ArrayList<>();
            for (Object v:list(value)) out.add(freeze(v));
            return Collections.unmodifiableList(out);
        }
        return value;
    }
    public static String write(Object value) {
        StringBuilder out = new StringBuilder();
        emit(value,out,0);
        return out.toString();
    }
    private static void emit(Object value,StringBuilder out,int depth) {
        if (depth>128) throw new Invalid();
        if (value==null) out.append("null");
        else if (value instanceof Boolean) out.append(value);
        else if (value instanceof Byte || value instanceof Short || value instanceof Integer || value instanceof Long) {
            long n=((Number)value).longValue();
            if(n < -9007199254740991L || n > 9007199254740991L) throw new Invalid();
            out.append(n);
        } else if (value instanceof String) quote((String)value,out);
        else if (value instanceof Map<?,?>) {
            out.append('{'); boolean first=true;
            for (Map.Entry<String,Object> e:new TreeMap<>(map(value)).entrySet()) {
                for(char c:e.getKey().toCharArray()) if(c>127) throw new Invalid();
                if(!first)out.append(','); first=false;
                quote(e.getKey(),out);out.append(':');emit(e.getValue(),out,depth+1);
            }
            out.append('}');
        } else if(value instanceof List<?>) {
            out.append('[');boolean first=true;
            for(Object v:list(value)){if(!first)out.append(',');first=false;emit(v,out,depth+1);}out.append(']');
        } else throw new Invalid();
    }
    private static void quote(String s,StringBuilder out) {
        out.append('"');
        for(int i=0;i<s.length();i++) {
            char c=s.charAt(i);
            switch(c) {
                case '"': out.append("\\\"");break;
                case '\\':out.append("\\\\");break;
                case '\b':out.append("\\b");break;
                case '\f':out.append("\\f");break;
                case '\n':out.append("\\n");break;
                case '\r':out.append("\\r");break;
                case '\t':out.append("\\t");break;
                default:
                    if(c<32) out.append(String.format("\\u%04x",(int)c));
                    else if(Character.isHighSurrogate(c)) {
                        if(i+1>=s.length() || !Character.isLowSurrogate(s.charAt(i+1)))throw new Invalid();
                        out.append(c).append(s.charAt(++i));
                    } else if(Character.isLowSurrogate(c))throw new Invalid();
                    else out.append(c);
            }
        }
        out.append('"');
    }
    public static String shaBytes(byte[] bytes) {
        try {
            byte[] d=MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder out=new StringBuilder();for(byte b:d)out.append(String.format("%02x",b & 255));return out.toString();
        } catch(NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    public static String hash(Object value){return shaBytes(write(value).getBytes(StandardCharsets.UTF_8));}
    private static final class Parser {
        final String s;int i;
        Parser(String s){this.s=s;}
        void space(){while(i<s.length() && " \t\r\n".indexOf(s.charAt(i))>=0)i++;}
        boolean take(char c){space();if(i<s.length()&&s.charAt(i)==c){i++;return true;}return false;}
        Object value(int depth) {
            if(depth>128)throw new Invalid();space();if(i>=s.length())throw new Invalid();char c=s.charAt(i);
            if(c=='"')return string();
            if(take('{')){
                Map<String,Object> m=new LinkedHashMap<>();if(take('}'))return m;
                do {space();String k=string();if(!take(':') || m.containsKey(k))throw new Invalid();m.put(k,value(depth+1));}while(take(','));
                if(!take('}'))throw new Invalid();return m;
            }
            if(take('[')){
                List<Object> a=new ArrayList<>();if(take(']'))return a;
                do{a.add(value(depth+1));}while(take(','));if(!take(']'))throw new Invalid();return a;
            }
            for(String literal:List.of("true","false","null"))if(s.startsWith(literal,i)){i+=literal.length();return literal.equals("null")?null:Boolean.valueOf(literal);}
            int begin=i;if(c=='-')i++;
            while(i<s.length() && s.charAt(i)>='0'&&s.charAt(i)<='9')i++;
            String n=s.substring(begin,i);
            if(!n.matches("0|-?[1-9][0-9]*"))throw new Invalid();
            BigInteger b=new BigInteger(n);if(b.abs().compareTo(BigInteger.valueOf(9007199254740991L))>0)throw new Invalid();return b.longValue();
        }
        String string(){
            if(i>=s.length()||s.charAt(i++)!='"')throw new Invalid();StringBuilder out=new StringBuilder();
            while(i<s.length()){
                char c=s.charAt(i++);if(c=='"')return out.toString();if(c<32)throw new Invalid();
                if(c!='\\'){out.append(c);continue;}if(i>=s.length())throw new Invalid();
                char e=s.charAt(i++);
                switch(e){
                    case '"':case '\\':case '/':out.append(e);break;
                    case 'b':out.append('\b');break;case 'f':out.append('\f');break;case 'n':out.append('\n');break;
                    case 'r':out.append('\r');break;case 't':out.append('\t');break;
                    case 'u':
                        if(i+4>s.length())throw new Invalid();
                        try{out.append((char)Integer.parseInt(s.substring(i,i+4),16));}catch(NumberFormatException ex){throw new Invalid();}i+=4;break;
                    default:throw new Invalid();
                }
            }
            throw new Invalid();
        }
    }
}
