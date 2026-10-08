import unittest
try:
    import cassis
except ImportError:
    cassis=None
from legalmath.prospectus.successor import annotation_authoring as draft, annotation_xmi as xmi
from legalmath.prospectus.successor.contracts import digest


@unittest.skipUnless(cassis is not None,'Cassis tests run separately in pinned sidecar')
class Authoring(unittest.TestCase):
    def setUp(self):
        self.text='😀 Alpha clause. Same. Same.\nExcept bankruptcy.'
        self.source={'document':'authoring-test','source_sha256':'a'*64,'text_sha256':digest(self.text.encode())}
        raw,self.types=draft.empty(self.text,self.source)
        self.cas=xmi.load_export(raw,self.types)

    def decode(self):
        return draft.decode(self.cas.to_xmi().encode(),self.source,self.text,types=self.types)['packet']

    def span(self,quote,key='g1',label='condition',start=0):
        a=self.text.index(quote,start)
        row=self.cas.typesystem.get_type(draft.SPAN)(begin=a,end=a+len(quote),groupId=key,label=label)
        self.cas.add(row);return row

    def edge(self,a,b,kind=xmi.GROUP_LINK):
        self.cas.add(self.cas.typesystem.get_type(draft.RELATION)(begin=b.begin,end=b.end,Governor=a,Dependent=b,
                     relationId='r1',kind=kind))

    def test_starts_without_labels(self):
        self.assertEqual(self.decode()['groups'],[])

    def test_new_span_boundary_change_and_deletion(self):
        ann=self.span('Alpha')
        self.assertEqual(self.decode()['groups'][0]['spans'][0]['begin'],3)
        self.cas.remove(ann)
        ann.end+=len(' clause')
        self.cas.add(ann)
        self.assertEqual(self.decode()['groups'][0]['spans'][0]['quote'],'Alpha clause')
        self.cas.remove(ann)
        self.assertEqual(self.decode()['groups'],[])

    def test_discontinuous_group_requires_actual_link(self):
        a=self.span('Alpha');b=self.span('bankruptcy')
        with self.assertRaisesRegex(ValueError,'discontinuity'):self.decode()
        self.edge(a,b)
        self.assertEqual(len(self.decode()['groups'][0]['spans']),2)

    def test_relation_between_groups_roundtrips(self):
        a=self.span('Alpha');b=self.span('bankruptcy','g2','exception');self.edge(a,b,'exception')
        self.assertEqual(self.decode()['relations'],[{'id':'r1','from':'g1','to':'g2','kind':'exception'}])

    def test_changed_source_rejected(self):
        self.cas.sofa_string=self.text.replace('Alpha','Omega')
        with self.assertRaisesRegex(ValueError,'text changed'):self.decode()

    def test_wrong_edition_rejected(self):
        next(iter(self.cas.select(xmi.IDENTITY))).sourceSHA='b'*64
        with self.assertRaisesRegex(ValueError,'edition'):self.decode()

    def test_duplicate_occurrence_preserves_second_position(self):
        ann=self.span('Same',start=self.text.index('Same')+1)
        self.assertEqual(self.decode()['groups'][0]['spans'][0]['begin'],ann.begin+1)

    def test_missing_identity_rejected(self):
        self.cas.remove(next(iter(self.cas.select(xmi.IDENTITY))))
        with self.assertRaisesRegex(ValueError,'identity'):self.decode()

    def test_dangling_relation_rejected(self):
        a=self.span('Alpha');b=self.span('bankruptcy','g2');self.edge(a,b,'exception')
        edge=next(iter(self.cas.select(draft.RELATION)));edge.Dependent=None
        with self.assertRaisesRegex(ValueError,'Dangling'):self.decode()

    def test_redirected_relation_offsets_rejected(self):
        a=self.span('Alpha');b=self.span('bankruptcy','g2');self.edge(a,b,'exception')
        edge=next(iter(self.cas.select(draft.RELATION)));edge.Dependent=a
        with self.assertRaisesRegex(ValueError,'target offsets'):self.decode()

    def test_conflicting_labels_rejected(self):
        a=self.span('Alpha');b=self.span('bankruptcy',label='exception');self.edge(a,b)
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.decode()

    def test_overlapping_group_members_rejected(self):
        a=self.span('Alpha');b=self.span('Alpha clause');self.edge(a,b)
        with self.assertRaisesRegex(ValueError,'overlapping'):self.decode()

    def test_duplicate_discontinuity_relation_rejected(self):
        a=self.span('Alpha');b=self.span('bankruptcy');self.edge(a,b)
        edge=next(iter(self.cas.select(draft.RELATION)))
        self.cas.add(self.cas.typesystem.get_type(draft.RELATION)(begin=b.begin,end=b.end,
            Governor=a,Dependent=b,relationId='r2',kind=xmi.GROUP_LINK))
        with self.assertRaisesRegex(ValueError,'Duplicate discontinuity'):self.decode()

    def test_semantic_relation_cannot_silently_change_group_endpoint(self):
        a=self.span('Alpha');b=self.span('bankruptcy');self.edge(a,b)
        target=self.span('Same','g2','exception')
        self.cas.add(self.cas.typesystem.get_type(draft.RELATION)(begin=target.begin,end=target.end,
            Governor=b,Dependent=target,relationId='r2',kind='exception'))
        with self.assertRaisesRegex(ValueError,'group heads'):self.decode()

    def test_mixed_imported_evidence_cannot_disappear(self):
        self.cas.add(self.cas.typesystem.get_type(xmi.SPAN)(begin=3,end=8,groupId='old',label='condition'))
        with self.assertRaisesRegex(ValueError,'Mixed'):self.decode()


if __name__=='__main__':unittest.main()
