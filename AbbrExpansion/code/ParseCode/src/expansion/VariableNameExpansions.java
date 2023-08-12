package expansion;

import java.util.Arrays;
import java.util.List;

/**
 * Expansions for an identifier
 */
public class VariableNameExpansions extends Expansions {
	private static List<String> key = Arrays.asList("type", "methodInvocated", "comment", "enclosingMethod", "enclosingClass", "parameterArgument", "assignment");

	public VariableNameExpansions() {
		super();
	}

	@Override
	protected void setType() {
		type = "VariableName";
	}

	@Override
	protected void setKey() {
		expansionKey = key;
	}

}
