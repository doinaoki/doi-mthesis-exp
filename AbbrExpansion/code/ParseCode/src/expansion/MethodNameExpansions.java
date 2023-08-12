package expansion;

import java.util.Arrays;
import java.util.List;

/**
 * Expansions for an identifier
 */
public class MethodNameExpansions extends Expansions {
	private static List<String> key = Arrays.asList("type", "siblings", "comment", "enclosingClass", "parameter", "assignment", "parameterArgument", "methodInvocated");


	public MethodNameExpansions() {
		super();
	}

	@Override
	protected void setType() {
		type = "MethodName";
	}

	@Override
	protected void setKey() {
		expansionKey = key;
	}
}
