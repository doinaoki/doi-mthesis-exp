package expansion;

import java.util.Arrays;
import java.util.List;

/**
 * Expansions for an identifier
 */
public class FieldNameExpansions extends Expansions {
	private static List<String> key = Arrays.asList("type", "siblings", "comment", "enclosingClass", "assignment", "methodInvocated", "parameterArgument");

	public FieldNameExpansions() {
		super();
	}

	@Override
	protected void setType() {
		type = "FieldName";
	}

	@Override
	protected void setKey() {
		expansionKey = key;
	}
}
