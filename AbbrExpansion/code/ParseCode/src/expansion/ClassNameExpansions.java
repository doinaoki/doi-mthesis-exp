package expansion;

import java.util.Arrays;
import java.util.List;

/**
 * Expansions for an identifier
 */
public class ClassNameExpansions extends Expansions {
	private static List<String> key = Arrays.asList("subclass", "subsubclass", "parents", "ancestor", "methods", "fields", "type", "comment");

	public ClassNameExpansions() {
		super();
	}

	@Override
	protected void setType() {
		type = "ClassName";
	}

	@Override
	protected void setKey() {
		expansionKey = key;
	}
}
