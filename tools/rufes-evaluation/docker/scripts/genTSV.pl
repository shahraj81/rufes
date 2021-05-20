#!/usr/bin/perl -w

%mentionidlist = ();

$old_doc_id = "this";
$entity_index = 101;
$doc_index = 100;

while (my $line = <>) {
    chomp $line;
    my ($sys_id, $mention_id, $mention_string, $mention_span, $entity_id, $entity_type, $mention_type, $confidence) = split ('\t', $line);
    my ($doc_id, $span) = split (':', $mention_span);
    my ($beg, $end) = split ("-", $span);
    my $entity_key = "$doc_id\-$entity_id";
    my @entity_type_list = split (';', $entity_type);
    #    print "$entity_type_list[0]\n";
    my @new_ent_list = ();
    foreach my $ent (@entity_type_list) {
	if ($ent !~ /\./) {
	    push (@new_ent_list, $ent);
	}
    }

    my @sorted_ent_list = sort @new_ent_list;
    my $new_entity_type = join (';', @sorted_ent_list);
    
    if ($doc_id ne $old_doc_id) {
	$entity_index = 101;
	$old_doc_id = $doc_id;
	$doc_index++;
	$mentionidlist{$entity_key} = "NIL$doc_index$entity_index";
	
    } else {
	if (! $mentionidlist{$entity_key}) {
	    $entity_index++;
	    $mentionidlist{$entity_key} = "NIL$doc_index$entity_index";
	}
    }
    
    print "$doc_id\t$beg\t$end\t$mentionidlist{$entity_key}\t$confidence\t$new_entity_type\n";
#    print "$mentionidlist{$entity_key}\t$entity_id\t$mention_string\n";
}
